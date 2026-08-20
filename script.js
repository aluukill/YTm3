document.addEventListener("DOMContentLoaded", () => {
  const convertForm = document.getElementById("convert-form");
  const youtubeUrlInput = document.getElementById("youtube-url");
  const clearBtn = document.getElementById("clear-btn");
  const pasteBtn = document.getElementById("paste-btn");
  const submitBtn = document.getElementById("submit-btn");
  const skeletonCard = document.getElementById("skeleton-card");
  const resultCard = document.getElementById("result-card");
  const videoThumb = document.getElementById("video-thumb");
  const videoTitle = document.getElementById("video-title");
  const videoChannel = document
    .getElementById("video-channel")
    .querySelector("span");
  const videoDuration = document.getElementById("video-duration");
  const audioPreview = document.getElementById("audio-preview");
  const downloadActionBtn = document.getElementById("download-action-btn");
  const downloadBtnIcon = downloadActionBtn.querySelector("i");
  const downloadBtnText = downloadActionBtn.querySelector("span");
  const copyLinkBtn = document.getElementById("copy-link-btn");
  const historySection = document.getElementById("history-section");
  const historyList = document.getElementById("history-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");
  const toast = document.getElementById("toast");
  const toastIcon = document.getElementById("toast-icon");
  const toastMessage = document.getElementById("toast-message");

  let currentVideoData = null;

  loadHistory();

  clearBtn.addEventListener("click", () => {
    youtubeUrlInput.value = "";
    youtubeUrlInput.focus();
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        youtubeUrlInput.value = text.trim();
        showToast("Pasted from clipboard", "info");
      }
    } catch (e) {
      showToast("Unable to read clipboard", "error");
    }
  });

  convertForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const url = youtubeUrlInput.value.trim();
    if (url) {
      processYouTubeUrl(url);
    }
  });

  copyLinkBtn.addEventListener("click", () => {
    if (downloadActionBtn.href && downloadActionBtn.href !== "#") {
      navigator.clipboard.writeText(downloadActionBtn.href);
      showToast("Direct audio link copied to clipboard!", "success");
    }
  });

  clearHistoryBtn.addEventListener("click", () => {
    localStorage.removeItem("ytm3_history");
    loadHistory();
    showToast("History cleared", "info");
  });

  function extractVideoId(url) {
    if (!url) return null;
    const str = url.trim();
    const regExp =
      /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?|shorts|live)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/ ]{11})/;
    const match = str.match(regExp);
    if (match && match[1]) return match[1];

    try {
      const parsed = new URL(str);
      if (parsed.searchParams.has("v")) {
        const v = parsed.searchParams.get("v");
        if (v && v.length === 11) return v;
      }
    } catch (e) {}

    return null;
  }

  async function processYouTubeUrl(rawUrl) {
    const videoId = extractVideoId(rawUrl);
    if (!videoId) {
      showToast("Invalid YouTube URL. Please check the link.", "error");
      return;
    }

    const cleanUrl = `https://www.youtube.com/watch?v=${videoId}`;

    resultCard.classList.add("hidden");
    skeletonCard.classList.remove("hidden");
    submitBtn.disabled = true;

    try {
      const response = await fetch("/api/info", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: cleanUrl }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to fetch video information");
      }

      const data = await response.json();

      currentVideoData = {
        id: data.id || videoId,
        url: cleanUrl,
        title: data.title || "YouTube Audio Track",
        author: data.author || "YouTube Channel",
        duration: data.duration || "00:00",
        thumbnail:
          data.thumbnail || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
      };

      videoThumb.src = currentVideoData.thumbnail;
      videoTitle.textContent = currentVideoData.title;
      videoChannel.textContent = currentVideoData.author;
      videoDuration.textContent = currentVideoData.duration;

      skeletonCard.classList.add("hidden");
      resultCard.classList.remove("hidden");

      setDownloadPreparing(true);
      const prepared = await prepareAudio(cleanUrl);
      if (!prepared) return;

      audioPreview.src = `/api/file/${prepared.file_id}`;
      downloadActionBtn.href = `/api/file/${prepared.file_id}?download=1`;
      downloadActionBtn.download = prepared.filename;
      downloadActionBtn.removeAttribute("target");
      setDownloadPreparing(false);

      saveToHistory(currentVideoData, "Max Quality");
      showToast("Audio ready for instant download!", "success");
    } catch (err) {
      skeletonCard.classList.add("hidden");
      showToast(err.message || "Failed to extract YouTube audio.", "error");
      setDownloadPreparing(false);
    } finally {
      submitBtn.disabled = false;
    }
  }

  async function prepareAudio(url) {
    try {
      const response = await fetch("/api/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: url }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to prepare audio");
      }

      const data = await response.json();
      if (!data.file_id) {
        throw new Error("Failed to prepare audio");
      }
      return data;
    } catch (err) {
      showToast(err.message || "Failed to prepare audio.", "error");
      return null;
    }
  }

  function setDownloadPreparing(preparing) {
    if (preparing) {
      downloadBtnIcon.className = "fa-solid fa-spinner fa-spin";
      downloadBtnText.textContent = "Preparing audio...";
      downloadActionBtn.classList.add("disabled");
    } else {
      downloadBtnIcon.className = "fa-solid fa-download";
      downloadBtnText.textContent = "Download Audio";
      downloadActionBtn.classList.remove("disabled");
    }
  }

  function saveToHistory(item, quality) {
    let history = JSON.parse(localStorage.getItem("ytm3_history") || "[]");
    history = history.filter((h) => h.id !== item.id);
    history.unshift({
      id: item.id,
      url: item.url,
      title: item.title,
      author: item.author,
      thumbnail: item.thumbnail,
      quality: quality,
      timestamp: new Date().toLocaleDateString(),
    });
    if (history.length > 10) history = history.slice(0, 10);
    localStorage.setItem("ytm3_history", JSON.stringify(history));
    loadHistory();
  }

  function loadHistory() {
    const history = JSON.parse(localStorage.getItem("ytm3_history") || "[]");
    if (history.length === 0) {
      historySection.classList.add("hidden");
      return;
    }

    historySection.classList.remove("hidden");
    historyList.innerHTML = "";

    history.forEach((item) => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML = `
                <div class="history-item-left">
                    <img src="${item.thumbnail}" class="history-thumb" alt="${item.title}">
                    <div class="history-details">
                        <span class="history-title">${item.title}</span>
                        <span class="history-meta">${item.author} &bull; ${item.quality}</span>
                    </div>
                </div>
                <div class="history-actions">
                    <button class="secondary-btn reload-hist-btn" data-url="${item.url}">
                        <i class="fa-solid fa-arrow-rotate-right"></i>
                    </button>
                </div>
            `;

      div.querySelector(".reload-hist-btn").addEventListener("click", () => {
        youtubeUrlInput.value = item.url;
        processYouTubeUrl(item.url);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });

      historyList.appendChild(div);
    });
  }

  function showToast(message, type = "info") {
    toastMessage.textContent = message;
    if (type === "success") {
      toastIcon.className = "fa-solid fa-circle-check";
      toastIcon.style.color = "#10b981";
    } else if (type === "error") {
      toastIcon.className = "fa-solid fa-circle-exclamation";
      toastIcon.style.color = "#ff3b5c";
    } else {
      toastIcon.className = "fa-solid fa-circle-info";
      toastIcon.style.color = "#3b82f6";
    }
    toast.classList.remove("hidden");

    setTimeout(() => {
      toast.classList.add("hidden");
    }, 3000);
  }
});
