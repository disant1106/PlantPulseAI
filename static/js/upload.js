const input = document.querySelector("#image");
const previewBox = document.querySelector("#previewBox");
const fileMeta = document.querySelector("#fileMeta");
const qualityList = document.querySelector("#qualityList");

function warningsFor(file) {
  const warnings = [];
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    warnings.push("Unsupported browser-reported type. Use JPG, PNG, or WebP.");
  }
  if (file.size < 50 * 1024) {
    warnings.push("Very small images can hide leaf symptoms.");
  }
  if (file.size > 8 * 1024 * 1024) {
    warnings.push("This file may exceed the default 8 MB upload limit.");
  }
  return warnings;
}

input?.addEventListener("change", () => {
  const file = input.files[0];
  if (!file) {
    previewBox.innerHTML = "<span>Preview appears here</span>";
    fileMeta.textContent = "No image selected";
    qualityList.innerHTML = "";
    return;
  }

  fileMeta.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB · ${file.type || "unknown type"}`;
  previewBox.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="Selected leaf preview">`;
  qualityList.innerHTML = warningsFor(file).map(item => `<div class="quality-item">${item}</div>`).join("");
});
