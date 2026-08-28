const API_URL = "http://localhost:8000";

// Global state for interactive filtering and sorting
let currentFindings = [];
let currentCode = "";
let activeCategory = "all";
let activeSort = "severity";

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    
    const form = document.getElementById("review-form");
    form.addEventListener("submit", handleFormSubmit);

    const codeInput = document.getElementById("code-input");
    const fileInput = document.getElementById("file-input");
    const fileName = document.getElementById("file-name");

    codeInput.addEventListener("input", () => {
        updateInputStats();
        if (codeInput.value.trim() !== "") {
            fileInput.value = "";
            fileName.textContent = "No file selected";
        }
    });

    fileInput.addEventListener("change", () => {
        const selectedFile = fileInput.files[0];
        if (selectedFile) {
            codeInput.value = "";
            fileName.textContent = `${selectedFile.name} (${formatBytes(selectedFile.size)})`;
        } else {
            fileName.textContent = "No file selected";
        }
        updateInputStats();
    });

    // Wire up filter category buttons
    const filterBtns = document.querySelectorAll(".filter-btn");
    filterBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            filterBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeCategory = btn.dataset.category;
            applyFiltersAndSort();
        });
    });

    // Wire up sorting selector
    const sortSelect = document.getElementById("sort-select");
    sortSelect.addEventListener("change", () => {
        activeSort = sortSelect.value;
        applyFiltersAndSort();
    });

    updateInputStats();
});

async function checkHealth() {
    const badge = document.getElementById("health-badge");
    try {
        const res = await fetch(`${API_URL}/health`);
        const data = await res.json();
        
        if (data.status === "ok") {
            badge.textContent = "Ollama: Connected";
            badge.className = "badge ok";
        } else {
            badge.textContent = "Ollama: Unreachable";
            badge.className = "badge error";
        }
    } catch (err) {
        console.error("Health check error:", err);
        badge.textContent = "Ollama: Unreachable";
        badge.className = "badge error";
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const code = document.getElementById("code-input").value;
    const file = document.getElementById("file-input").files[0];
    const mode = document.getElementById("mode-select").value;
    const question = document.getElementById("question-input").value;

    const loader = document.getElementById("loader");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    const resultSection = document.getElementById("result-section");
    const submitBtn = document.getElementById("submit-btn");
    const formHint = document.getElementById("form-hint");

    if (!code.trim() && !file) {
        formHint.textContent = "Paste code or upload a supported file before running an audit.";
        formHint.className = "form-hint error";
        return;
    }

    formHint.textContent = "";
    formHint.className = "form-hint";
    errorCard.classList.add("hidden");
    resultSection.classList.add("hidden");
    loader.classList.remove("hidden");
    submitBtn.disabled = true;
    submitBtn.textContent = "Analyzing Code...";

    const formData = new FormData();
    if (file) {
        formData.append("file", file);
    } else {
        formData.append("code", code);
    }
    
    if (mode && mode !== "auto") {
        formData.append("mode", mode);
    }
    if (question.trim()) {
        formData.append("question", question);
    }

    try {
        const response = await fetch(`${API_URL}/review`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "An error occurred during code analysis.");
        }

        // Capture submitted code in memory for side-by-side highlighting
        if (file) {
            const readPromise = new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = function(ev) {
                    resolve(ev.target.result);
                };
                reader.readAsText(file);
            });
            currentCode = await readPromise;
            document.getElementById("code-viewer-filename").textContent = file.name;
        } else {
            currentCode = code;
            document.getElementById("code-viewer-filename").textContent = "Pasted Code";
        }

        currentFindings = data.findings || [];

        renderResults(data);
        applyFiltersAndSort();
        resultSection.classList.remove("hidden");
    } catch (err) {
        console.error("Review request failed:", err);
        errorMessage.textContent = err.message || "Failed to connect to review server.";
        errorCard.classList.remove("hidden");
    } finally {
        loader.classList.add("hidden");
        submitBtn.disabled = false;
        submitBtn.textContent = "Run Audit";
        checkHealth();
    }
}

function renderResults(result) {
    const riskBadge = document.getElementById("risk-badge");
    const submissionType = document.getElementById("res-submission-type");
    const summaryText = document.getElementById("res-summary-text");
    const findingCount = document.getElementById("res-finding-count");
    const topSeverity = document.getElementById("res-top-severity");

    riskBadge.textContent = `${result.overall_risk_level} Risk`;
    riskBadge.className = `badge risk-${result.overall_risk_level}`;
    
    submissionType.textContent = titleCase(result.submission_type.replace("_", " "));
    const totalFindings = result.findings ? result.findings.length : 0;
    findingCount.textContent = totalFindings;
    topSeverity.textContent = getTopSeverity(result.findings);
    summaryText.textContent = result.summary;

    // Calculate breakdowns
    const findings = result.findings || [];
    const counts = {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        info: 0
    };
    
    const catCounts = {
        security: 0,
        bug: 0,
        architecture: 0,
        clean_code: 0,
        performance: 0
    };

    findings.forEach(f => {
        if (counts[f.severity] !== undefined) counts[f.severity]++;
        if (catCounts[f.category] !== undefined) catCounts[f.category]++;
    });

    // Update severity breakdown bar chart and badges
    const severities = ["critical", "high", "medium", "low", "info"];
    severities.forEach(sev => {
        const pct = totalFindings > 0 ? (counts[sev] / totalFindings) * 100 : 0;
        const barSlice = document.getElementById(`bar-${sev}`);
        if (barSlice) {
            barSlice.style.width = `${pct}%`;
        }
        
        const badge = document.getElementById(`badge-${sev}`);
        if (badge) {
            badge.textContent = `${counts[sev]} ${titleCase(sev)}`;
            badge.style.display = counts[sev] > 0 ? "inline-flex" : "none";
        }
    });

    // Update category breakdown count badges
    const categories = ["security", "bug", "architecture", "clean_code", "performance"];
    const categoryEmojis = {
        security: "🔴 Security",
        bug: "🐛 Bug",
        architecture: "🏛️ Architecture",
        clean_code: "🧼 Clean Code",
        performance: "⚡ Performance"
    };
    
    categories.forEach(cat => {
        const badge = document.getElementById(`badge-cat-${cat}`);
        if (badge) {
            badge.textContent = `${categoryEmojis[cat]}: ${catCounts[cat]}`;
            badge.style.display = catCounts[cat] > 0 ? "inline-flex" : "none";
        }
    });
}

function applyFiltersAndSort() {
    const findingsList = document.getElementById("findings-list");
    const noFindingsCard = document.getElementById("no-findings-card");

    // 1. Filter findings
    let filtered = [...currentFindings];
    if (activeCategory !== "all") {
        filtered = filtered.filter(f => f.category === activeCategory);
    }

    // 2. Sort findings
    const severityRank = {
        critical: 5,
        high: 4,
        medium: 3,
        low: 2,
        info: 1
    };

    if (activeSort === "severity") {
        filtered.sort((a, b) => {
            const rankA = severityRank[a.severity] || 0;
            const rankB = severityRank[b.severity] || 0;
            if (rankB !== rankA) {
                return rankB - rankA;
            }
            // Fallback: sort by line number
            const lineA = a.line_start !== null ? a.line_start : Infinity;
            const lineB = b.line_start !== null ? b.line_start : Infinity;
            return lineA - lineB;
        });
    } else if (activeSort === "line") {
        filtered.sort((a, b) => {
            const lineA = a.line_start !== null ? a.line_start : Infinity;
            const lineB = b.line_start !== null ? b.line_start : Infinity;
            return lineA - lineB;
        });
    }

    // 3. Render Code Viewer with highlighted lines matching filtered findings
    const lineClasses = {};
    filtered.forEach(f => {
        if (f.line_start !== null && f.line_start !== undefined) {
            const start = f.line_start;
            const end = f.line_end !== null && f.line_end !== undefined ? f.line_end : start;
            for (let l = start; l <= end; l++) {
                const currentSev = lineClasses[l];
                if (!currentSev || severityRank[f.severity] > severityRank[currentSev]) {
                    lineClasses[l] = f.severity;
                }
            }
        }
    });

    let highlightedCode = "";
    if (typeof hljs !== "undefined" && currentCode.trim() !== "") {
        try {
            const isDiff = currentCode.startsWith("diff --git") || currentCode.includes("\n+++ ") || currentCode.includes("\n--- ");
            highlightedCode = hljs.highlight(currentCode, { language: isDiff ? "diff" : "python" }).value;
        } catch (e) {
            console.error("Highlighting error:", e);
            highlightedCode = escapeHTML(currentCode);
        }
    } else {
        highlightedCode = escapeHTML(currentCode);
    }

    const codeLines = highlightedCode.split(/\r?\n/);
    let codeHtml = "";
    for (let i = 0; i < codeLines.length; i++) {
        const lineNum = i + 1;
        const highlightClass = lineClasses[lineNum] ? ` highlight-${lineClasses[lineNum]}` : "";
        codeHtml += `<div class="code-line${highlightClass}" id="code-line-${lineNum}" data-line="${lineNum}">`;
        codeHtml += `<span class="line-number">${lineNum}</span>`;
        codeHtml += `<span class="line-text">${codeLines[i] || " "}</span>`;
        codeHtml += `</div>`;
    }
    
    const codeContainer = document.getElementById("code-container");
    if (codeContainer) {
        codeContainer.innerHTML = codeHtml;
    }

    // 4. Render Findings List
    findingsList.innerHTML = "";

    if (filtered.length === 0) {
        noFindingsCard.classList.remove("hidden");
        const h3 = noFindingsCard.querySelector("h3");
        const p = noFindingsCard.querySelector("p");
        if (currentFindings.length === 0) {
            h3.textContent = "No Issues Detected";
            p.textContent = "The code looks clean, efficient, and secure! No findings were reported.";
        } else {
            h3.textContent = "No Matches";
            p.textContent = `No findings match the active filter category "${activeCategory.replace("_", " ")}".`;
        }
    } else {
        noFindingsCard.classList.add("hidden");

        const categoryHeaders = {
            security: "🔴 Security",
            bug: "🐛 Bug",
            architecture: "🏛️ Architecture",
            clean_code: "🧼 Clean Code",
            performance: "⚡ Performance"
        };

        filtered.forEach(f => {
            const card = document.createElement("div");
            card.className = `finding-card ${f.severity}`;

            // Determine if suggestion should be collapsed by default (low/info = collapsed, medium+ = expanded)
            const isCollapsed = f.severity === "low" || f.severity === "info";
            const collapseClass = isCollapsed ? " collapsed" : "";
            const arrowText = isCollapsed ? "▼" : "▲";

            let linesStr = "N/A";
            if (f.line_start !== null && f.line_start !== undefined) {
                if (f.line_end !== null && f.line_end !== undefined && f.line_end !== f.line_start) {
                    linesStr = `Lines ${f.line_start}-${f.line_end}`;
                } else {
                    linesStr = `Line ${f.line_start}`;
                }
            }

            card.innerHTML = `
                <div class="finding-header">
                    <div class="finding-meta">
                        <span class="finding-severity ${f.severity}">${f.severity.toUpperCase()}</span>
                        <span class="finding-lines">${linesStr}</span>
                        <span class="category-icon-label" title="${f.category}">${categoryHeaders[f.category] || f.category}</span>
                    </div>
                    <span class="finding-confidence">Confidence: ${Math.round(f.confidence * 100)}%</span>
                </div>
                <p class="finding-desc">${escapeHTML(f.description)}</p>
                <div class="finding-suggestion-box${collapseClass}">
                    <div class="finding-suggestion-header" onclick="toggleSuggestion(this)">
                        <span>Actionable Suggestion / Fix</span>
                        <span class="toggle-arrow">${arrowText}</span>
                    </div>
                    <div class="finding-suggestion-content">
                        <p>${escapeHTML(f.suggestion)}</p>
                    </div>
                </div>
            `;

            // Intercept card clicks to scroll to code line on left
            card.addEventListener("click", (e) => {
                if (e.target.closest(".finding-suggestion-box")) {
                    return; // Ignore suggestion toggle clicks
                }

                if (f.line_start !== null && f.line_start !== undefined) {
                    const lineEl = document.getElementById(`code-line-${f.line_start}`);
                    if (lineEl) {
                        lineEl.scrollIntoView({ behavior: "smooth", block: "center" });
                        
                        // Apply flash anim
                        lineEl.classList.add("flash-active");
                        setTimeout(() => {
                            lineEl.classList.remove("flash-active");
                        }, 1500);
                    }
                }
            });

            findingsList.appendChild(card);
        });
    }
}

// Collapsible Suggestion toggle function
window.toggleSuggestion = function(headerElement) {
    const box = headerElement.parentElement;
    box.classList.toggle("collapsed");
    const arrow = headerElement.querySelector(".toggle-arrow");
    if (box.classList.contains("collapsed")) {
        arrow.textContent = "▼";
    } else {
        arrow.textContent = "▲";
    }
};

function updateInputStats() {
    const codeInput = document.getElementById("code-input");
    const fileInput = document.getElementById("file-input");
    const inputStats = document.getElementById("input-stats");
    const code = codeInput.value;
    const file = fileInput.files[0];

    if (file) {
        inputStats.textContent = formatBytes(file.size);
        return;
    }

    if (!code.trim()) {
        inputStats.textContent = "0 lines";
        return;
    }

    const lines = code.split(/\r\n|\r|\n/).length;
    inputStats.textContent = `${lines} ${lines === 1 ? "line" : "lines"} / ${formatBytes(new Blob([code]).size)}`;
}

function getTopSeverity(findings = []) {
    if (!findings || findings.length === 0) return "None";

    const severityRank = {
        info: 1,
        low: 2,
        medium: 3,
        high: 4,
        critical: 5
    };

    const top = findings.reduce((current, finding) => {
        const currentRank = severityRank[current] || 0;
        const nextRank = severityRank[finding.severity] || 0;
        return nextRank > currentRank ? finding.severity : current;
    }, "info");

    return titleCase(top);
}

function titleCase(value) {
    return value
        .split(" ")
        .filter(Boolean)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatBytes(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, index);
    return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function escapeHTML(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
