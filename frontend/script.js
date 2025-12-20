const BACKEND_URL = "http://127.0.0.1:8000";

// State management
let chatHistory = [];
let currentVideoId = null;
let isVideoLoaded = false;

// DOM elements
const videoUrlInput = document.getElementById("videoUrl");
const loadBtn = document.getElementById("loadBtn");
const loadStatus = document.getElementById("loadStatus");
const videoInfo = document.getElementById("videoInfo");
const videoIdDisplay = document.getElementById("videoId");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const exportBtn = document.getElementById("exportBtn");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  loadChatHistory();
  
  // Enter key to send message
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !sendBtn.disabled) {
      sendMessage();
    }
  });
  
  // Enter key to load video
  videoUrlInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !loadBtn.disabled) {
      loadVideo();
    }
  });
});

// Load Video
loadBtn.onclick = loadVideo;

async function loadVideo() {
  const videoUrl = videoUrlInput.value.trim();
  
  if (!videoUrl) {
    showStatus("Please enter a YouTube URL", "error");
    return;
  }
  
  // Show loading state
  loadBtn.disabled = true;
  loadBtn.querySelector(".btn-text").textContent = "Loading...";
  loadBtn.querySelector(".btn-loader").style.display = "inline";
  showStatus("Loading video... This may take 30-60 seconds", "loading");
  
  try {
    const res = await fetch(`${BACKEND_URL}/load_video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_url: videoUrl }),
    });
    
    const data = await res.json();
    
    if (!res.ok) {
      handleLoadError(res.status, data);
      return;
    }
    
    // Success!
    currentVideoId = data.video_id;
    isVideoLoaded = true;
    
    showStatus("Video loaded successfully! " + (data.cached ? "(From cache)" : ""), "success");
    videoIdDisplay.textContent = `Video ID: ${currentVideoId}`;
    videoInfo.style.display = "block";
    
    // Clear OLD chat history from localStorage FIRST
    localStorage.removeItem("chatHistory");
    
    // Clear chat display and history
    clearChat(false);
    chatHistory = []; // Reset array
    
    // Enable chat
    chatInput.disabled = false;
    sendBtn.disabled = false;
    clearBtn.disabled = false;
    exportBtn.disabled = false;
    chatInput.focus();
    
    // Show system message AFTER clearing
    addSystemMessage(`✅ Video loaded! You can now ask questions about it.`);
    
    // Save to localStorage
    localStorage.setItem("lastVideoId", currentVideoId);
    
  } catch (err) {
    showStatus("Cannot connect to backend. Is the server running?", "error");
    console.error(err);
  } finally {
    loadBtn.disabled = false;
    loadBtn.querySelector(".btn-text").textContent = "Load Video";
    loadBtn.querySelector(".btn-loader").style.display = "none";
  }
}

function handleLoadError(status, data) {
  if (status === 503 && data.error === "YouTube Rate Limit") {
    let errorHtml = `<strong>⚠️ YouTube Rate Limit</strong><br>${data.message}<br><br><strong>Solutions:</strong><ul style="text-align:left;display:inline-block;">`;
    data.solutions.forEach(s => {
      errorHtml += `<li>${s}</li>`;
    });
    errorHtml += "</ul>";
    loadStatus.innerHTML = errorHtml;
    loadStatus.className = "load-status error";
  } else {
    showStatus(data.detail || "Failed to load video", "error");
  }
}

function showStatus(message, type) {
  loadStatus.textContent = message;
  loadStatus.className = `load-status ${type}`;
}

// Send Message
sendBtn.onclick = sendMessage;

async function sendMessage() {
  const question = chatInput.value.trim();
  
  if (!question) return;
  
  if (!isVideoLoaded) {
    addSystemMessage("Please load a video first!");
    return;
  }
  
  // Add user message
  addMessage(question, "user");
  chatInput.value = "";
  
  // Disable input while processing
  chatInput.disabled = true;
  sendBtn.disabled = true;
  
  // Show typing indicator
  const typingId = addTypingIndicator();
  
  try {
    const res = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    
    const data = await res.json();
    
    // Remove typing indicator
    removeTypingIndicator(typingId);
    
    if (!res.ok) {
      addSystemMessage(`Error: ${data.detail || "Failed to get answer"}`);
      return;
    }
    
    // Add assistant message
    addMessage(data.answer, "assistant");
    
  } catch (err) {
    removeTypingIndicator(typingId);
    addSystemMessage("Cannot connect to backend. Is the server running?");
    console.error(err);
  } finally {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// Add message to chat
function addMessage(text, role) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  
  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.textContent = text;
  
  const timeSpan = document.createElement("span");
  timeSpan.className = "message-time";
  timeSpan.textContent = getCurrentTime();
  
  messageDiv.appendChild(contentDiv);
  messageDiv.appendChild(timeSpan);
  
  // Remove welcome message if it exists
  const welcomeMsg = chatMessages.querySelector(".welcome-message");
  if (welcomeMsg) {
    welcomeMsg.remove();
  }
  
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  // Save to history
  chatHistory.push({
    text,
    role,
    timestamp: new Date().toISOString()
  });
  saveChatHistory();
}

function addSystemMessage(text) {
  const messageDiv = document.createElement("div");
  messageDiv.className = "message assistant";
  messageDiv.style.textAlign = "center";
  
  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.style.background = "#fff3cd";
  contentDiv.style.color = "#856404";
  contentDiv.style.border = "1px solid #ffeaa7";
  contentDiv.textContent = text;
  
  messageDiv.appendChild(contentDiv);
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
  const id = `typing-${Date.now()}`;
  const messageDiv = document.createElement("div");
  messageDiv.className = "message assistant";
  messageDiv.id = id;
  
  const typingDiv = document.createElement("div");
  typingDiv.className = "typing-indicator";
  typingDiv.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;
  
  messageDiv.appendChild(typingDiv);
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  return id;
}

function removeTypingIndicator(id) {
  const element = document.getElementById(id);
  if (element) {
    element.remove();
  }
}

function getCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

// Clear Chat
clearBtn.onclick = () => {
  if (confirm("Are you sure you want to clear the chat history?")) {
    clearChat(true);
  }
};

function clearChat(showWelcome = true) {
  chatMessages.innerHTML = "";
  chatHistory = [];
  saveChatHistory();
  
  if (showWelcome) {
    chatMessages.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-icon">👋</div>
        <h3>Chat cleared!</h3>
        <p>Start a new conversation about the video.</p>
      </div>
    `;
  }
}

// Export Chat
exportBtn.onclick = () => {
  if (chatHistory.length === 0) {
    alert("No chat history to export");
    return;
  }
  
  const exportData = {
    video_id: currentVideoId,
    exported_at: new Date().toISOString(),
    messages: chatHistory
  };
  
  const dataStr = JSON.stringify(exportData, null, 2);
  const blob = new Blob([dataStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement("a");
  a.href = url;
  a.download = `chat-history-${currentVideoId}-${Date.now()}.json`;
  a.click();
  
  URL.revokeObjectURL(url);
};

// Local Storage
function saveChatHistory() {
  localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

function loadChatHistory() {
  // Don't auto-restore chat history on page load
  // Only restore if it's for the same session
  
  const saved = localStorage.getItem("chatHistory");
  const lastVideoId = localStorage.getItem("lastVideoId");
  
  // Only restore chat if we have a saved video
  if (saved && lastVideoId) {
    try {
      const savedHistory = JSON.parse(saved);
      
      // Only restore if there are messages
      if (savedHistory.length > 0) {
        chatHistory = savedHistory;
        chatMessages.innerHTML = "";
        
        savedHistory.forEach(msg => {
          const messageDiv = document.createElement("div");
          messageDiv.className = `message ${msg.role}`;
          
          const contentDiv = document.createElement("div");
          contentDiv.className = "message-content";
          contentDiv.textContent = msg.text;
          
          const timeSpan = document.createElement("span");
          timeSpan.className = "message-time";
          timeSpan.textContent = new Date(msg.timestamp).toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
          });
          
          messageDiv.appendChild(contentDiv);
          messageDiv.appendChild(timeSpan);
          chatMessages.appendChild(messageDiv);
        });
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
      // Clear corrupted data
      localStorage.removeItem("chatHistory");
    }
  }
  
  // Restore last video info
  if (lastVideoId) {
    currentVideoId = lastVideoId;
    isVideoLoaded = true;
    videoIdDisplay.textContent = `Video ID: ${currentVideoId}`;
    videoInfo.style.display = "block";
    chatInput.disabled = false;
    sendBtn.disabled = false;
    clearBtn.disabled = false;
    exportBtn.disabled = false;
  }
}