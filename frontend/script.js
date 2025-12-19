const BACKEND_URL = "http://127.0.0.1:8000";

const loadBtn = document.getElementById("loadBtn");
const askBtn = document.getElementById("askBtn");

loadBtn.onclick = async () => {
  const videoUrl = document.getElementById("videoUrl").value;
  const status = document.getElementById("loadStatus");

  if (!videoUrl.trim()) {
    status.innerText = "Please enter a YouTube URL";
    status.style.color = "red";
    return;
  }

  status.innerText = "Loading video... (this may take 30-60 seconds)";
  status.style.color = "blue";
  
  // Disable button during loading
  loadBtn.disabled = true;

  try {
    const res = await fetch(`${BACKEND_URL}/load_video`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ video_url: videoUrl }),
    });

    const data = await res.json();

    if (!res.ok) {
      // Handle rate limiting specially
      if (res.status === 503 && data.error === "YouTube Rate Limit") {
        status.innerHTML = `
          <strong style="color: red;">⚠️ YouTube Rate Limit Detected</strong><br>
          <p>${data.message}</p>
          <strong>Solutions:</strong>
          <ul style="text-align: left; display: inline-block;">
            ${data.solutions.map(s => `<li>${s}</li>`).join('')}
          </ul>
        `;
      } else {
        status.innerText = `Error: ${data.detail || "Failed to load video"}`;
        status.style.color = "red";
      }
      loadBtn.disabled = false;
      return;
    }

    status.innerText = `✅ Video loaded successfully! ${data.cached ? '(From cache)' : ''}`;
    status.style.color = "green";
    loadBtn.disabled = false;

  } catch (err) {
    status.innerText = "❌ Cannot connect to backend. Is the server running?";
    status.style.color = "red";
    loadBtn.disabled = false;
    console.error(err);
  }
};

askBtn.onclick = async () => {
  const question = document.getElementById("question").value;
  const answerBox = document.getElementById("answer");

  if (!question.trim()) {
    answerBox.innerText = "Please enter a question";
    answerBox.style.color = "red";
    return;
  }

  answerBox.innerText = "Thinking...";
  answerBox.style.color = "blue";
  
  // Disable button during processing
  askBtn.disabled = true;

  try {
    const res = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    const data = await res.json();

    if (!res.ok) {
      answerBox.innerText = `Error: ${data.detail || "Failed to get answer"}`;
      answerBox.style.color = "red";
      askBtn.disabled = false;
      return;
    }

    answerBox.innerText = data.answer;
    answerBox.style.color = "black";
    askBtn.disabled = false;

  } catch (err) {
    answerBox.innerText = "❌ Cannot connect to backend. Is the server running?";
    answerBox.style.color = "red";
    askBtn.disabled = false;
    console.error(err);
  }
};