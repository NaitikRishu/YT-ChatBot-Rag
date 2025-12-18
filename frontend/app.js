async function ask() {
  const video = document.getElementById("video").value;
  const question = document.getElementById("question").value;

  const res = await fetch("http://127.0.0.1:8000/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      video_url: video,
      question: question
    })
  });

  const data = await res.json();
  document.getElementById("answer").innerText = data.answer;
}

