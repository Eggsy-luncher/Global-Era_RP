const serverSelectBtn = document.getElementById("serverSelectBtn");
const serverSelectMenu = document.getElementById("serverSelectMenu");
const topFlag = document.getElementById("topFlag");
const topRegion = document.getElementById("topRegion");

if (serverSelectBtn && serverSelectMenu && topFlag && topRegion) {
  serverSelectBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    serverSelectMenu.classList.toggle("open");
  });

  document.querySelectorAll(".server-select-option").forEach(option => {
    option.addEventListener("click", () => {
      topRegion.textContent = option.dataset.server;
      topFlag.textContent = option.dataset.flag;
      serverSelectBtn.textContent = `${option.dataset.server} ▼`;
      serverSelectMenu.classList.remove("open");
    });
  });
}

document.addEventListener("click", () => {
  if (serverSelectMenu) serverSelectMenu.classList.remove("open");
});