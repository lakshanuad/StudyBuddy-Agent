import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from agents import Runner

from commands import process_study_command, parse_quiz_command
from quiz.session import QuizSession
from quiz.generator import generate_quiz_from_lectures

console = Console()


def display_welcome_banner():
    """Renders the startup welcome banner."""
    banner_content = (
        "[bold white]An agentic study assistant powered by Groq, LangChain, and ChromaDB.[/bold white]\n"
        "[dim]Ask questions directly about your lecture PDFs or use specialized study modes below.[/dim]"
    )
    console.print(
        Panel(
            banner_content,
            title="[bold cyan]📚 Welcome to StudyBuddy[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )


def display_help_table():
    """Renders a colorful, clean table of available study commands."""
    table = Table(title="StudyBuddy Commands & Study Modes", border_style="dim")
    table.add_column("Command", style="bold green", no_wrap=True)
    table.add_column("Study Mode / Action", style="cyan")
    table.add_column("Example Usage", style="yellow")

    table.add_row(
        "/quiz [topic] [--questions N] [--difficulty easy|medium|hard]",
        "Interactive MCQ quiz with automated grading",
        "/quiz requirements --questions 5 --difficulty medium",
    )
    table.add_row("/flashcards [topic]", "High-yield flashcards with front/back concepts", "/flashcards agile models")
    table.add_row("/summary [topic]", "Structured cheat-sheet & concept summary", "/summary software project management")
    table.add_row("/feynman [concept]", "Plain English explanation with real-world analogies", "/feynman critical path method")
    table.add_row("/clear", "Reset conversational memory for a fresh session", "/clear")
    table.add_row("/history", "View active interaction turn count", "/history")
    table.add_row("/help", "Show this command reference table", "/help")
    table.add_row("exit / quit", "Exit the application", "exit")

    console.print(table)


def render_question_panel(session: QuizSession):
    """Renders the current question and options in a clean terminal panel."""
    q = session.get_current_question()
    if not q:
        return

    content = f"[bold white]{q.question}[/bold white]\n\n"
    for opt_key in ("A", "B", "C", "D"):
        opt_text = q.options.get(opt_key, "")
        content += f"  [bold cyan]{opt_key})[/bold cyan] {opt_text}\n"

    title = f"[bold cyan]Question {session.current_question_number}/{session.total_questions}[/bold cyan] [dim]| Topic: {session.topic} ({session.difficulty.capitalize()})[/dim]"
    console.print(
        Panel(
            content.strip(),
            title=title,
            border_style="cyan",
            padding=(1, 2),
        )
    )


def render_quiz_results(session: QuizSession):
    """Renders final quiz score, statistics, and grade category."""
    result = session.get_results()
    if not result:
        return

    grade_colors = {
        "Excellent": "bold green",
        "Very Good": "bold cyan",
        "Good": "bold blue",
        "Needs Improvement": "bold yellow",
        "Needs More Practice": "bold red",
    }
    color = grade_colors.get(result.grade, "bold white")

    table = Table(title="📊 QUIZ RESULTS", border_style="cyan", show_header=False)
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="yellow")

    table.add_row("Topic", result.topic)
    table.add_row("Difficulty", result.difficulty.capitalize())
    table.add_row("Total Questions", str(result.total_questions))
    table.add_row("Correct Answers", f"[green]{result.correct_count}[/green]")
    table.add_row("Incorrect Answers", f"[red]{result.incorrect_count}[/red]")
    table.add_row("Final Score", f"[{color}]{result.score_percentage}%[/{color}]")
    table.add_row("Grade", f"[{color}]{result.grade}[/{color}]")

    console.print()
    console.print(table)
    console.print()


def render_question_review(question_results, title="Quiz Review"):
    """Renders question-by-question review with student answer, correct answer, and citations."""
    if not question_results:
        console.print("[bold green]🎉 Perfect score! No incorrect answers to review.[/bold green]\n")
        return

    console.print(f"\n[bold cyan]📖 {title}[/bold cyan]\n")
    for qr in question_results:
        q = qr.question
        status_icon = "[bold green]✅ Correct[/bold green]" if qr.is_correct else "[bold red]❌ Incorrect[/bold red]"
        student_ans = qr.student_answer or "No answer"

        review_text = (
            f"[bold white]{q.question}[/bold white]\n\n"
            f"• Your Answer: [bold {'green' if qr.is_correct else 'red'}]{student_ans}[/bold {'green' if qr.is_correct else 'red'}]\n"
            f"• Correct Answer: [bold green]{q.correct_answer}[/bold green] - {q.options.get(q.correct_answer, '')}\n\n"
            f"[bold]Explanation:[/bold] {q.explanation}\n"
            f"[dim]Source: {q.source}[/dim]"
        )

        border = "green" if qr.is_correct else "red"
        console.print(
            Panel(
                review_text,
                title=f"Question {q.id}: {status_icon}",
                border_style=border,
                padding=(1, 2),
            )
        )
        console.print()


async def run_interactive_quiz(console: Console, retriever, topic: str, num_questions: int, difficulty: str):
    """Orchestrates an interactive quiz session from generation to evaluation and review."""
    target_topic = topic if topic else "Course Lecture Notes"

    with console.status(
        f"[bold cyan]📚 Searching lecture materials & generating {num_questions} questions on '{target_topic}'...[/bold cyan]",
        spinner="dots",
    ):
        quiz_data, err = await generate_quiz_from_lectures(
            retriever=retriever,
            topic=target_topic,
            num_questions=num_questions,
            difficulty=difficulty,
        )

    if err or not quiz_data:
        console.print(f"\n[bold red][Quiz Generation Error]:[/bold red] {err or 'Could not generate quiz.'}\n")
        return

    session = QuizSession(quiz_data)
    session.start()

    console.print()
    console.print(
        Panel(
            f"[bold white]Topic:[/bold white] {session.topic}\n"
            f"[bold white]Difficulty:[/bold white] {session.difficulty.capitalize()}\n"
            f"[bold white]Total Questions:[/bold white] {session.total_questions}\n\n"
            "[dim]Answer each question by entering A, B, C, or D.\nType '/quitquiz' at any time to exit quiz mode.[/dim]",
            title="[bold green]🎯 Quiz Starting[/bold green]",
            border_style="green",
        )
    )
    console.print()

    # Question Answering Loop
    while not session.is_completed:
        render_question_panel(session)

        # Answer input validation loop
        while True:
            try:
                user_choice = console.input("[bold yellow]Your answer (A/B/C/D)[/bold yellow] [dim]or /quitquiz[/dim] > ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]Quiz cancelled. Exited quiz mode.[/bold yellow]\n")
                return

            if not user_choice:
                continue

            # Check quiz cancel command
            if user_choice.lower() in ("/quitquiz", "/quit", "/exit", "quit", "exit"):
                console.print("\n[bold yellow]Quiz cancelled. Exited quiz mode.[/bold yellow]\n")
                return

            # Submit answer
            success = session.submit_answer(user_choice)
            if success:
                console.print("[dim]Answer recorded.[/dim]\n")
                session.next_question()
                break
            else:
                console.print("[bold red]Invalid option. Please enter A, B, C, or D (or /quitquiz to cancel).[/bold red]")

    # All questions answered -> Display Results
    render_quiz_results(session)

    # Post-Quiz Interactive Menu
    while True:
        console.print("[bold cyan]What would you like to do next?[/bold cyan]")
        console.print("  [bold green]1)[/bold green] Review incorrect answers")
        console.print("  [bold green]2)[/bold green] Review all answers & explanations")
        console.print("  [bold green]3)[/bold green] Retry this quiz")
        console.print("  [bold green]4)[/bold green] Generate a new quiz on this topic")
        console.print("  [bold green]5)[/bold green] Exit quiz mode")

        try:
            choice = console.input("[bold yellow]Select an option (1-5)[/bold yellow] > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Exited quiz mode.[/bold yellow]\n")
            break

        if choice == "1":
            incorrect = session.review_answers(incorrect_only=True)
            render_question_review(incorrect, title="Review: Incorrect Answers")
        elif choice == "2":
            all_res = session.review_answers(incorrect_only=False)
            render_question_review(all_res, title="Review: All Answers & Explanations")
        elif choice == "3":
            console.print("\n[bold yellow]🔄 Resetting responses. Retrying quiz...[/bold yellow]\n")
            session.reset()
            while not session.is_completed:
                render_question_panel(session)
                while True:
                    try:
                        user_choice = console.input("[bold yellow]Your answer (A/B/C/D)[/bold yellow] [dim]or /quitquiz[/dim] > ").strip()
                    except (KeyboardInterrupt, EOFError):
                        console.print("\n[bold yellow]Quiz cancelled.[/bold yellow]\n")
                        return
                    if not user_choice:
                        continue
                    if user_choice.lower() in ("/quitquiz", "/quit", "/exit", "quit", "exit"):
                        console.print("\n[bold yellow]Quiz cancelled.[/bold yellow]\n")
                        return
                    if session.submit_answer(user_choice):
                        console.print("[dim]Answer recorded.[/dim]\n")
                        session.next_question()
                        break
                    else:
                        console.print("[bold red]Invalid option. Please enter A, B, C, or D.[/bold red]")
            render_quiz_results(session)
        elif choice == "4":
            console.print(f"\n[bold cyan]🔄 Generating fresh quiz on '{target_topic}'...[/bold cyan]\n")
            await run_interactive_quiz(console, retriever, topic=target_topic, num_questions=num_questions, difficulty=difficulty)
            break
        elif choice in ("5", "", "exit", "quit", "q"):
            console.print("[bold yellow]Exited quiz mode.[/bold yellow]\n")
            break
        else:
            console.print("[dim]Please enter a valid choice (1-5).[/dim]\n")


async def start_cli_session(agent, retriever=None):
    """Runs the interactive CLI study session with rich terminal formatting and memory."""
    console.print()
    display_welcome_banner()
    console.print()
    display_help_table()
    console.print()

    history_inputs = []
    turn_count = 0

    while True:
        try:
            user_input = console.input("[bold green]You[/bold green] [dim]>[/dim] ").strip()
            if not user_input:
                continue

            # Check exit commands
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[bold yellow]🎓 Goodbye and happy studying![/bold yellow]\n")
                break

            # Check help command
            if user_input.lower() in ("/help", "/h", "help"):
                console.print()
                display_help_table()
                console.print()
                continue

            # Check clear command
            if user_input.lower() in ("/clear", "/reset", "clear"):
                history_inputs = []
                turn_count = 0
                console.print("\n[bold magenta]🧹 Session memory cleared. Starting fresh![/bold magenta]\n")
                continue

            # Check history command
            if user_input.lower() in ("/history", "/turns"):
                console.print(f"\n[bold blue]🧠 Active session: {turn_count} turn(s) stored in context memory.[/bold blue]\n")
                continue

            # Check enhanced interactive /quiz command
            quiz_cmd = parse_quiz_command(user_input)
            if quiz_cmd:
                if retriever is not None:
                    await run_interactive_quiz(
                        console=console,
                        retriever=retriever,
                        topic=quiz_cmd["topic"],
                        num_questions=quiz_cmd["num_questions"],
                        difficulty=quiz_cmd["difficulty"],
                    )
                    continue
                else:
                    console.print("[yellow]Retriever not attached. Falling back to agent quiz generation...[/yellow]")

            # Process other study slash commands (/flashcards, /summary, /feynman)
            prompt, mode_label = process_study_command(user_input)

            if mode_label:
                console.print(f"[bold magenta]⚡ [{mode_label} Activated][/bold magenta]")

            # Run agent with animated spinner
            with console.status("[bold cyan]🔍 Searching lecture notes & thinking...[/bold cyan]", spinner="dots"):
                current_input = history_inputs + [{"role": "user", "content": prompt}]
                result = await Runner.run(agent, input=current_input)

            # Update conversation memory
            history_inputs = result.to_input_list()
            turn_count += 1

            # Render response as structured, styled markdown panel
            rendered_markdown = Markdown(result.final_output)
            console.print()
            console.print(
                Panel(
                    rendered_markdown,
                    title="[bold cyan]🎓 StudyBuddy[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )
            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Session ended. Goodbye! 🎓[/bold yellow]\n")
            break
        except Exception as e:
            console.print(f"\n[bold red][Error encountered]:[/bold red] {e}\n")
