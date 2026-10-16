/* Browser frontend for the same-origin FastAPI service. */
const API = "";
const $ = (id) => document.getElementById(id);
let currentJob = "";

$("key").value = sessionStorage.getItem("vidcut-api-key") || "";
$("key").addEventListener("input", () => {
  sessionStorage.setItem("vidcut-api-key", $("key").value);
});

function authHeaders(extra = {}) {
  const key = $("key").value.trim();
  return key ? { ...extra, "X-API-Key": key } : extra;
}

$("go").addEventListener("click", async () => {
  $("err").textContent = "";
  const consent = $("consent").checked;
  if (!consent) return fail("Centang persetujuan pemilik suara dulu.");
  const text = $("teks").value.trim();
  if (!text) return fail("Teks tidak boleh kosong.");
  const yt = $("yt").value.trim();
  const file = $("file").files[0];
  if (!yt && !file) return fail("Sertakan link YouTube atau file audio.");
  if (yt && file) return fail("Pilih salah satu sumber saja.");

  $("go").disabled = true;
  $("prog-card").hidden = false;
  $("player").hidden = true;
  $("dl-row").hidden = true;
  setBar(2, "Mengirim job...");

  try {
    let response;
    if (file) {
      const form = new FormData();
      form.append("upload", file);
      form.append("text", text);
      form.append("language", $("lang").value);
      form.append("consent", "true");
      response = await fetch(`${API}/api/jobs/upload`, {
        method: "POST", headers: authHeaders(), body: form,
      });
    } else {
      response = await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          youtube_url: yt,
          start_seconds: Number($("start").value || 0),
          duration_seconds: Number($("dur").value || 30),
          text,
          language: $("lang").value,
          consent: true,
        }),
      });
    }
    if (!response.ok) throw new Error(await errText(response));
    currentJob = (await response.json()).id;
    await monitor(currentJob);
  } catch (error) {
    fail(error.message || String(error));
    $("go").disabled = false;
  }
});

async function monitor(jobId) {
  while (true) {
    const response = await fetch(`${API}/api/jobs/${jobId}`, {
      headers: authHeaders(), cache: "no-store",
    });
    if (!response.ok) throw new Error(await errText(response));
    const status = await response.json();
    setBar(status.progress || 0, status.stage_detail || status.status);
    $("warn").textContent = status.warning || "";
    if (status.status === "failed") {
      throw new Error(status.error || "Proses gagal.");
    }
    if (status.status === "done") {
      await showResult(jobId);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

async function authenticatedBlob(jobId, format) {
  const response = await fetch(`${API}/api/jobs/${jobId}/audio?format=${format}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await errText(response));
  return URL.createObjectURL(await response.blob());
}

async function showResult(jobId) {
  setBar(100, "Selesai");
  const wavUrl = await authenticatedBlob(jobId, "wav");
  const mp3Url = await authenticatedBlob(jobId, "mp3");
  $("player").src = wavUrl;
  $("dl-wav").href = wavUrl;
  $("dl-wav").download = `voice-clone-${jobId}.wav`;
  $("dl-mp3").href = mp3Url;
  $("dl-mp3").download = `voice-clone-${jobId}.mp3`;
  $("player").hidden = false;
  $("dl-row").hidden = false;
  $("go").disabled = false;
}

$("del").addEventListener("click", async () => {
  if (!currentJob) return;
  const response = await fetch(`${API}/api/jobs/${currentJob}`, {
    method: "DELETE", headers: authHeaders(),
  });
  if (!response.ok) return fail(await errText(response));
  $("player").hidden = true;
  $("dl-row").hidden = true;
  $("prog-card").hidden = true;
  currentJob = "";
});

function setBar(percent, text) {
  $("bar").style.width = `${percent}%`;
  $("stage").textContent = text;
}

function fail(message) {
  $("err").textContent = message;
}

async function errText(response) {
  try {
    return (await response.json()).detail || `Error ${response.status}`;
  } catch {
    return `Error ${response.status}`;
  }
}
