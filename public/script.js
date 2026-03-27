const STATUS_ENDPOINT = "http://127.0.0.1:5000/status";

function statusColorClass(status) {
  if (status.includes("Human")) return "text-status-human";
  if (status.includes("Elephant")) return "text-status-elephant";
  if (status.includes("Bear")) return "text-status-bear";
  if (status.includes("Giraffe")) return "text-status-giraffe";
  return "text-status-safe";
}

function statusDot(status) {
  if (status.includes("Human")) return "🔴";
  if (status.includes("Elephant")) return "🟠";
  if (status.includes("Bear")) return "🟣";
  if (status.includes("Giraffe")) return "🟡";
  return "🟢";
}

async function updateDetectionStatus() {
  const statusElement = document.getElementById("status");
  if (!statusElement) return;

  try {
    const response = await fetch(STATUS_ENDPOINT);
    if (!response.ok) return;

    const data = await response.json();
    const status = data.status || "Nothing Detected";

    statusElement.textContent = `${statusDot(status)} ${status}`;
    statusElement.classList.remove(
      "text-status-human",
      "text-status-elephant",
      "text-status-bear",
      "text-status-giraffe",
      "text-status-safe"
    );
    statusElement.classList.add(statusColorClass(status));
  } catch (_error) {
    statusElement.textContent = "🟢 Nothing Detected";
    statusElement.classList.remove(
      "text-status-human",
      "text-status-elephant",
      "text-status-bear",
      "text-status-giraffe"
    );
    statusElement.classList.add("text-status-safe");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateDetectionStatus();
  setInterval(updateDetectionStatus, 500);
});
