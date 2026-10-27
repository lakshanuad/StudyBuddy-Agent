/* ==========================================================================
   StudyBuddy Minimalist Frontend Application Logic
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let conversationHistory = [];
    let currentQuiz = null;
    let currentQuestionIndex = 0;
    let quizScore = 0;
    let quizUserAnswers = [];
    let isSubmittingChat = false;

    // DOM Elements - Navigation
    const tabBtns = document.querySelectorAll(".tab-btn");
    const viewPanels = document.querySelectorAll(".view-panel");
    const statusLabel = document.getElementById("statusLabel");
    const docCountNum = document.getElementById("docCountNum");

    // DOM Elements - Chat
    const chatMessages = document.getElementById("chatMessages");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const clearChatBtn = document.getElementById("clearChatBtn");
    const welcomeHero = document.getElementById("welcomeHero");
    const quickPromptBtns = document.querySelectorAll(".quick-card");
    const chipBtns = document.querySelectorAll(".chip-btn[data-prefix]");

    // DOM Elements - Quiz
    const quizForm = document.getElementById("quizForm");
    const quizTopicInput = document.getElementById("quizTopicInput");
    const generateQuizBtn = document.getElementById("generateQuizBtn");
    const quizConfigCard = document.getElementById("quizConfigCard");
    const quizActiveCard = document.getElementById("quizActiveCard");
    const quizResultsCard = document.getElementById("quizResultsCard");
    const quizProgressFill = document.getElementById("quizProgressFill");
    const activeTopicBadge = document.getElementById("activeTopicBadge");
    const activeStepBadge = document.getElementById("activeStepBadge");
    const activeQuestionText = document.getElementById("activeQuestionText");
    const activeOptionsList = document.getElementById("activeOptionsList");
    const quizFeedbackBanner = document.getElementById("quizFeedbackBanner");
    const feedbackTitle = document.getElementById("feedbackTitle");
    const feedbackExplanation = document.getElementById("feedbackExplanation");
    const feedbackCitation = document.getElementById("feedbackCitation");
    const nextQuestionBtn = document.getElementById("nextQuestionBtn");
    const retakeQuizBtn = document.getElementById("retakeQuizBtn");

    // DOM Elements - Documents
    const docsGrid = document.getElementById("docsGrid");
    const reindexBtn = document.getElementById("reindexBtn");
    const dropzone = document.getElementById("dropzone");
    const pdfFileInput = document.getElementById("pdfFileInput");
    const browseFilesBtn = document.getElementById("browseFilesBtn");

    /* ==========================================================================
       1. Navigation & Tab Switching
       ========================================================================== */
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            tabBtns.forEach(b => b.classList.remove("active"));
            viewPanels.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) targetPanel.classList.add("active");

            if (targetId === "docsView") {
                loadDocuments();
            }
        });
    });

    /* ==========================================================================
       2. System Status & Initialization
       ========================================================================== */
    async function checkSystemStatus() {
        try {
            const res = await fetch("/api/status");
            if (!res.ok) throw new Error("Status check failed");
            const data = await res.json();
            
            statusLabel.textContent = `Online • ${data.model}`;
            docCountNum.textContent = data.document_count || "0";
        } catch (err) {
            statusLabel.textContent = "Offline";
            console.error("Status error:", err);
        }
    }

    checkSystemStatus();

    /* ==========================================================================
       3. Chat & Agent Interaction
       ========================================================================== */

    // Auto-resize chat textarea
    chatInput.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + "px";
    });

    // Enter key to send (Shift+Enter for newline)
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendChat();
        }
    });

    sendBtn.addEventListener("click", handleSendChat);

    // Quick chips
    chipBtns.forEach(chip => {
        chip.addEventListener("click", () => {
            const prefix = chip.getAttribute("data-prefix");
            chatInput.value = prefix;
            chatInput.focus();
        });
    });

    // Quick prompt cards
    quickPromptBtns.forEach(card => {
        card.addEventListener("click", () => {
            const prompt = card.getAttribute("data-prompt");
            chatInput.value = prompt;
            handleSendChat();
        });
    });

    // Clear chat memory
    clearChatBtn.addEventListener("click", () => {
        conversationHistory = [];
        chatMessages.innerHTML = "";
        if (welcomeHero) {
            chatMessages.appendChild(welcomeHero);
        }
        chatInput.value = "";
    });

    async function handleSendChat() {
        const text = chatInput.value.trim();
        if (!text || isSubmittingChat) return;

        // Hide welcome hero if still visible
        if (welcomeHero && welcomeHero.parentNode === chatMessages) {
            welcomeHero.remove();
        }

        // Add user message bubble
        appendMessage("user", text);
        chatInput.value = "";
        chatInput.style.height = "auto";

        // Add thinking bubble
        const thinkingId = appendThinkingBubble();
        isSubmittingChat = true;
        sendBtn.disabled = true;

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    history: conversationHistory
                })
            });

            removeThinkingBubble(thinkingId);

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Agent failed to respond.");
            }

            const data = await res.json();
            conversationHistory = data.history || [];
            
            appendMessage("assistant", data.reply, data.mode_label);
        } catch (err) {
            removeThinkingBubble(thinkingId);
            appendMessage("assistant", `⚠️ **Error:** ${err.message}`);
        } finally {
            isSubmittingChat = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    function appendMessage(role, content, modeLabel = null) {
        const row = document.createElement("div");
        row.className = `message-row ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "You" : "SB";

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        if (modeLabel) {
            const modePill = document.createElement("div");
            modePill.style.cssText = "font-size: 0.72rem; font-weight: 700; color: #818cf8; margin-bottom: 0.4rem; text-transform: uppercase;";
            modePill.textContent = `⚡ [${modeLabel} Mode]`;
            bubble.appendChild(modePill);
        }

        // Render Markdown for assistant or plain text for user
        if (role === "assistant" && typeof marked !== "undefined") {
            const renderedHtml = marked.parse(content);
            const contentDiv = document.createElement("div");
            contentDiv.innerHTML = renderedHtml;
            bubble.appendChild(contentDiv);
        } else {
            const p = document.createElement("p");
            p.textContent = content;
            bubble.appendChild(p);
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendThinkingBubble() {
        const id = "thinking-" + Date.now();
        const row = document.createElement("div");
        row.className = "message-row assistant";
        row.id = id;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = "SB";

        const bubble = document.createElement("div");
        bubble.className = "message-bubble thinking-bubble";
        bubble.innerHTML = `
            <span>Searching notes & thinking</span>
            <div class="thinking-dots">
                <span></span><span></span><span></span>
            </div>
        `;

        row.appendChild(avatar);
        row.appendChild(bubble);
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    function removeThinkingBubble(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    /* ==========================================================================
       4. Interactive Knowledge Quiz
       ========================================================================== */

    // Setup segmented button selection
    function setupSegmentedGroup(groupId) {
        const group = document.getElementById(groupId);
        if (!group) return;
        const buttons = group.querySelectorAll(".segment-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => {
                buttons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });
    }

    setupSegmentedGroup("difficultyGroup");
    setupSegmentedGroup("countGroup");

    function getSelectedSegment(groupId) {
        const active = document.querySelector(`#${groupId} .segment-btn.active`);
        return active ? active.getAttribute("data-value") : null;
    }

    // Generate Quiz
    quizForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const topic = quizTopicInput.value.trim();
        if (!topic) return;

        const difficulty = getSelectedSegment("difficultyGroup") || "medium";
        const count = parseInt(getSelectedSegment("countGroup") || "5", 10);

        setQuizLoading(true);

        try {
            const res = await fetch("/api/quiz/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    topic: topic,
                    num_questions: count,
                    difficulty: difficulty
                })
            });

            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || "Failed to generate quiz.");
            }

            currentQuiz = data.quiz;
            startQuizSession();
        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setQuizLoading(false);
        }
    });

    function setQuizLoading(isLoading) {
        generateQuizBtn.disabled = isLoading;
        const textSpan = generateQuizBtn.querySelector(".btn-text");
        if (textSpan) {
            textSpan.textContent = isLoading ? "Generating Questions..." : "Generate Quiz";
        }
    }

    function startQuizSession() {
        if (!currentQuiz || !currentQuiz.questions.length) return;

        currentQuestionIndex = 0;
        quizScore = 0;
        quizUserAnswers = [];

        quizConfigCard.style.display = "none";
        quizResultsCard.style.display = "none";
        quizActiveCard.style.display = "flex";

        activeTopicBadge.textContent = currentQuiz.topic;
        renderCurrentQuestion();
    }

    function renderCurrentQuestion() {
        const q = currentQuiz.questions[currentQuestionIndex];
        const total = currentQuiz.questions.length;

        // Update progress
        const percent = ((currentQuestionIndex + 1) / total) * 100;
        quizProgressFill.style.width = `${percent}%`;
        activeStepBadge.textContent = `Question ${currentQuestionIndex + 1} of ${total}`;

        // Question text
        activeQuestionText.textContent = q.question;

        // Reset feedback
        quizFeedbackBanner.style.display = "none";
        nextQuestionBtn.style.display = "none";

        // Render Options
        activeOptionsList.innerHTML = "";
        const optionsMap = q.options || {};
        const letters = ["A", "B", "C", "D"];

        letters.forEach(letter => {
            const text = optionsMap[letter];
            if (!text) return;

            const btn = document.createElement("button");
            btn.className = "option-btn";
            btn.setAttribute("data-letter", letter);
            btn.innerHTML = `
                <span class="opt-letter">${letter}</span>
                <span class="opt-text">${text}</span>
            `;

            btn.addEventListener("click", () => handleSelectAnswer(letter, q));
            activeOptionsList.appendChild(btn);
        });
    }

    function handleSelectAnswer(selectedLetter, question) {
        const optionBtns = activeOptionsList.querySelectorAll(".option-btn");
        optionBtns.forEach(btn => btn.classList.add("locked"));

        const isCorrect = selectedLetter.toUpperCase() === question.correct_answer.toUpperCase();
        if (isCorrect) quizScore++;

        const sourceCitation = question.source || question.source_document || "Course Lecture Notes";
        quizUserAnswers.push({
            question: question.question,
            selected: selectedLetter,
            correct: question.correct_answer,
            isCorrect: isCorrect,
            explanation: question.explanation,
            citation: sourceCitation
        });

        // Highlight selected and truth
        optionBtns.forEach(btn => {
            const letter = btn.getAttribute("data-letter");
            if (letter === selectedLetter) {
                btn.classList.add(isCorrect ? "selected-correct" : "selected-incorrect");
            }
            if (letter === question.correct_answer && !isCorrect) {
                btn.classList.add("show-truth");
            }
        });

        // Show feedback banner
        quizFeedbackBanner.style.display = "flex";
        quizFeedbackBanner.className = `quiz-feedback-banner ${isCorrect ? "feedback-banner-correct" : "feedback-banner-incorrect"}`;
        feedbackTitle.textContent = isCorrect ? "Correct!" : `Incorrect (Correct: Option ${question.correct_answer})`;
        feedbackExplanation.textContent = question.explanation;
        feedbackCitation.textContent = `📚 Source: ${sourceCitation}`;

        // Show next button
        nextQuestionBtn.style.display = "inline-flex";
        const isLast = currentQuestionIndex === currentQuiz.questions.length - 1;
        nextQuestionBtn.textContent = isLast ? "View Final Results →" : "Next Question →";
    }

    nextQuestionBtn.addEventListener("click", () => {
        if (currentQuestionIndex < currentQuiz.questions.length - 1) {
            currentQuestionIndex++;
            renderCurrentQuestion();
        } else {
            showQuizResults();
        }
    });

    function showQuizResults() {
        quizActiveCard.style.display = "none";
        quizResultsCard.style.display = "flex";

        const total = currentQuiz.questions.length;
        const percentage = Math.round((quizScore / total) * 100);

        document.getElementById("scorePercent").textContent = `${percentage}%`;
        document.getElementById("scoreRatio").textContent = `${quizScore} / ${total} Correct`;

        const titleEl = document.getElementById("scoreTitle");
        const subEl = document.getElementById("scoreSubtitle");

        if (percentage >= 80) {
            titleEl.textContent = "Outstanding Mastery! 🌟";
            subEl.textContent = `Excellent comprehension of ${currentQuiz.topic}.`;
        } else if (percentage >= 60) {
            titleEl.textContent = "Solid Understanding! 👍";
            subEl.textContent = "Good progress, but review the explanations below for tricky concepts.";
        } else {
            titleEl.textContent = "Room for Improvement 📖";
            subEl.textContent = "Consider using /summary or /flashcards to strengthen your foundational notes.";
        }

        // Render Breakdown
        const breakdownEl = document.getElementById("resultsBreakdown");
        breakdownEl.innerHTML = "";

        quizUserAnswers.forEach((item, idx) => {
            const div = document.createElement("div");
            div.className = `result-item ${item.isCorrect ? "result-item-correct" : "result-item-incorrect"}`;
            div.innerHTML = `
                <div class="result-item-header">
                    <span>Q${idx + 1}: ${item.question}</span>
                    <span style="color: ${item.isCorrect ? "var(--accent-emerald)" : "var(--accent-rose)"}">
                        ${item.isCorrect ? "✓ Correct" : `✗ Chosen: ${item.selected} | Correct: ${item.correct}`}
                    </span>
                </div>
                <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.35rem;">
                    ${item.explanation}
                </div>
                <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 0.25rem;">
                    ${item.citation}
                </div>
            `;
            breakdownEl.appendChild(div);
        });
    }

    retakeQuizBtn.addEventListener("click", () => {
        quizResultsCard.style.display = "none";
        quizConfigCard.style.display = "block";
    });

    /* ==========================================================================
       5. Document Library & Ingestion
       ========================================================================== */

    async function loadDocuments() {
        try {
            const res = await fetch("/api/documents");
            const data = await res.json();
            renderDocumentsGrid(data.documents || []);
        } catch (err) {
            console.error("Failed to load documents:", err);
        }
    }

    function renderDocumentsGrid(docs) {
        docsGrid.innerHTML = "";
        if (!docs.length) {
            docsGrid.innerHTML = `<p style="color: var(--text-muted); font-size: 0.88rem;">No PDF documents found in ./lectures. Upload some below.</p>`;
            return;
        }

        docs.forEach(doc => {
            const card = document.createElement("div");
            card.className = "doc-card";
            card.innerHTML = `
                <div class="doc-card-top">
                    <div class="doc-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                    </div>
                    <div class="doc-info">
                        <div class="doc-name" title="${doc.name}">${doc.name}</div>
                        <div class="doc-meta">${doc.size_kb} KB • Modified ${doc.last_modified}</div>
                    </div>
                </div>
                <div class="doc-status-badge">
                    <span>●</span> Indexed & Vectorized
                </div>
            `;
            docsGrid.appendChild(card);
        });

        docCountNum.textContent = docs.length;
    }

    // Reindex button
    reindexBtn.addEventListener("click", async () => {
        reindexBtn.disabled = true;
        reindexBtn.textContent = "Re-indexing ChromaDB...";

        try {
            const res = await fetch("/api/documents/reindex", { method: "POST" });
            const data = await res.json();
            alert(data.message || "Re-indexing complete!");
            loadDocuments();
            checkSystemStatus();
        } catch (err) {
            alert(`Re-indexing failed: ${err.message}`);
        } finally {
            reindexBtn.disabled = false;
            reindexBtn.innerHTML = `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                </svg> Re-index Vector Store
            `;
        }
    });

    // File Upload handling
    browseFilesBtn.addEventListener("click", () => pdfFileInput.click());

    pdfFileInput.addEventListener("change", (e) => {
        if (e.target.files.length) {
            uploadPdf(e.target.files[0]);
        }
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length) {
            uploadPdf(e.dataTransfer.files[0]);
        }
    });

    async function uploadPdf(file) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            alert("Only PDF documents are supported.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        const dropText = dropzone.querySelector("h3");
        const originalText = dropText.textContent;
        dropText.textContent = `Uploading & Vectorizing ${file.name}...`;

        try {
            const res = await fetch("/api/documents/upload", {
                method: "POST",
                body: formData
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Upload failed");

            alert(data.message);
            loadDocuments();
            checkSystemStatus();
        } catch (err) {
            alert(`Upload error: ${err.message}`);
        } finally {
            dropText.textContent = originalText;
            pdfFileInput.value = "";
        }
    }
});
