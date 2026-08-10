const serverSelectBtn = document.getElementById("serverSelectBtn");
const serverSelectMenu = document.getElementById("serverSelectMenu");
const topFlag = document.getElementById("topFlag");
const topRegion = document.getElementById("topRegion");

function showLoginPrompt(serverName) {
  const old = document.getElementById("loginModal");
  if (old) old.remove();

  const modal = document.createElement("div");
  modal.id = "loginModal";
  modal.innerHTML = `
    <div class="login-modal-backdrop"></div>
    <div class="login-modal-box">
      <h3>Login Required</h3>
      <p>Please log in to join the <strong>${serverName}</strong> server.</p>
      <div class="login-modal-actions">
        <button type="button" class="btn primary" id="loginDiscordBtn">Login with Discord</button>
        <button type="button" class="btn ghost" id="loginLaterBtn">Maybe Later</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const style = document.createElement("style");
  style.textContent = `
    #loginModal {
      position: fixed; inset: 0; z-index: 9999;
      display: flex; align-items: center; justify-content: center;
    }
    .login-modal-backdrop {
      position: absolute; inset: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(4px);
    }
    .login-modal-box {
      position: relative;
      background: #11161a;
      border: 1px solid #2d3439;
      border-radius: 12px;
      padding: 28px 32px;
      max-width: 360px;
      width: 90%;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.6);
    }
    .login-modal-box h3 {
      margin: 0 0 10px;
      color: #f5cf22;
      font-size: 20px;
    }
    .login-modal-box p {
      margin: 0 0 22px;
      color: #c0c5c9;
      font-size: 14px;
      line-height: 1.5;
    }
    .login-modal-actions {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .login-modal-actions .btn {
      width: 100%;
      padding: 12px;
      border-radius: 6px;
      font-weight: 900;
      font-size: 13px;
      cursor: pointer;
      border: none;
    }
    .login-modal-actions .btn.primary {
      background: #5865F2;
      color: #fff;
    }
    .login-modal-actions .btn.ghost {
      background: transparent;
      border: 1px solid #3a4248;
      color: #aaa;
    }
  `;
  document.head.appendChild(style);

  document.getElementById("loginLaterBtn").addEventListener("click", () => {
    modal.remove();
  });

  document.getElementById("loginDiscordBtn").addEventListener("click", () => {
    window.open("https://discord.gg/aSEFdRGSB", "_blank");
    modal.remove();
  });

  modal.querySelector(".login-modal-backdrop").addEventListener("click", () => {
    modal.remove();
  });
}

if (serverSelectBtn && serverSelectMenu && topFlag && topRegion) {
  serverSelectBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    serverSelectMenu.classList.toggle("open");
  });

  document.querySelectorAll(".server-select-option").forEach(option => {
    option.addEventListener("click", () => {
      const server = option.dataset.server;
      const flag = option.dataset.flag;

      topRegion.textContent = server;
      topFlag.textContent = flag;
      serverSelectBtn.textContent = server + " ▼";
      serverSelectMenu.classList.remove("open");

      showLoginPrompt(server);
    });
  });
}

document.addEventListener("click", () => {
  if (serverSelectMenu) serverSelectMenu.classList.remove("open");
});