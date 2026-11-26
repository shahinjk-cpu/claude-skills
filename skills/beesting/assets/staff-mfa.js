/* Двухфакторный вход персонала: пароль + код из приложения (TOTP, Supabase MFA).
   StaffMFA.ensure(sb, mount, { onSignOut, issuer }) → Promise<boolean>:
   mount — контейнер (внутри может быть .card), issuer — название в приложении-аутентификаторе.
   true — сессия подтверждена кодом (aal2), false — не удалось проверить.
   Первый вход: показывает QR для Google Authenticator / Яндекс Ключа и просит код.
   Дальше: просит только 6-значный код. */
(() => {
  'use strict';

  let ISSUER = 'Сайт';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
    ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));

  function codeForm(intro) {
    return `
      ${intro}
      <label for="mfaCode">Код из приложения</label>
      <input id="mfaCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6"
             pattern="[0-9]{6}" placeholder="000000"
             style="text-align:center;letter-spacing:8px;font-size:22px">
      <button id="mfaOk" style="width:100%;margin-top:14px">Подтвердить</button>
      <button id="mfaOut" class="ghost" style="width:100%;margin-top:10px">Выйти</button>
      <div id="mfaMsg" class="msg" role="alert"></div>`;
  }

  function wire(mount, factorId, sb, done, onSignOut) {
    const input = mount.querySelector('#mfaCode');
    const btn = mount.querySelector('#mfaOk');
    const msg = mount.querySelector('#mfaMsg');
    let busy = false;
    async function submit() {
      const code = input.value.replace(/\D/g, '');
      if (code.length !== 6) { msg.textContent = 'Введите 6 цифр из приложения.'; input.focus(); return; }
      if (busy) return;
      busy = true; btn.disabled = true; msg.textContent = 'Проверяем…';
      const { error } = await sb.auth.mfa.challengeAndVerify({ factorId, code });
      busy = false; btn.disabled = false;
      if (error) {
        msg.textContent = /invalid|expired/i.test(error.message)
          ? 'Неверный или устаревший код. Подождите новый код и введите ещё раз.'
          : /rate|too many/i.test(error.message)
            ? 'Слишком много попыток. Подождите минуту.'
            : 'Не получилось: ' + error.message;
        input.select();
        return;
      }
      msg.textContent = '';
      done();
    }
    btn.onclick = submit;
    input.addEventListener('input', () => {
      input.value = input.value.replace(/\D/g, '').slice(0, 6);
      if (input.value.length === 6) submit();
    });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
    mount.querySelector('#mfaOut').onclick = () => onSignOut?.();
    input.focus();
  }

  function showError(mount, text, onSignOut) {
    mount.innerHTML = `<h1>Вход по коду</h1>
      <div class="msg" role="alert" style="margin-top:8px">${esc(text)}</div>
      <button id="mfaOut" class="ghost" style="width:100%;margin-top:14px">Выйти</button>`;
    mount.querySelector('#mfaOut').onclick = () => onSignOut?.();
  }

  async function ensure(sb, mount, { onSignOut, issuer } = {}) {
    if (issuer) ISSUER = String(issuer);
    const card = mount.querySelector('.card') || mount;
    const { data: aal, error } = await sb.auth.mfa.getAuthenticatorAssuranceLevel();
    if (error) { mount.classList.remove('hide'); showError(card, 'Не удалось проверить вход: ' + error.message, onSignOut); return false; }
    if (aal.currentLevel === 'aal2') { mount.classList.add('hide'); return true; }

    const { data: factors, error: listError } = await sb.auth.mfa.listFactors();
    if (listError) { mount.classList.remove('hide'); showError(card, 'Не удалось проверить вход: ' + listError.message, onSignOut); return false; }
    mount.classList.remove('hide');

    return new Promise(resolve => {
      const done = () => { mount.classList.add('hide'); card.innerHTML = ''; resolve(true); };
      const verified = (factors.totp || []).find(f => f.status === 'verified');

      if (verified) {
        card.innerHTML = `<h1>Код из приложения</h1>` +
          codeForm(`<div class="who" style="margin:6px 0 4px">Откройте Google Authenticator или Яндекс Ключ и введите код «${ISSUER}».</div>`);
        wire(card, verified.id, sb, done, onSignOut);
        return;
      }

      (async () => {
        // Незавершённые прошлые попытки привязки мешают новой — убираем их.
        const stale = (factors.all || []).filter(f => f.factor_type === 'totp' && f.status !== 'verified');
        for (const f of stale) await sb.auth.mfa.unenroll({ factorId: f.id });

        const { data, error: enrollError } = await sb.auth.mfa.enroll({
          factorType: 'totp',
          issuer: ISSUER,
          friendlyName: ISSUER + ' ' + new Date().toISOString().slice(0, 16).replace('T', ' '),
        });
        if (enrollError) { showError(card, 'Не удалось включить вход по коду: ' + enrollError.message, onSignOut); resolve(false); return; }

        const qr = String(data.totp?.qr_code || '');
        const secret = String(data.totp?.secret || '');
        card.innerHTML = `<h1>Защитите вход</h1>
          <div class="who" style="margin:6px 0 10px">Один раз привяжите телефон — дальше при входе понадобится код из приложения.</div>
          <ol style="margin:0 0 10px 18px;padding:0;font-size:14px;line-height:1.5">
            <li>Установите Google Authenticator или Яндекс Ключ.</li>
            <li>Отсканируйте QR-код в приложении.</li>
            <li>Введите 6-значный код ниже.</li>
          </ol>
          ${/^data:image\/svg\+xml/.test(qr) ? `<img src="${esc(qr)}" alt="QR-код для приложения" width="200" height="200"
              style="display:block;margin:6px auto;background:#fff;border-radius:12px;padding:8px">` : ''}
          <div class="who" style="text-align:center;margin-bottom:6px">Не сканируется? Введите ключ вручную:<br>
            <code style="user-select:all;word-break:break-all;font-size:13px">${esc(secret)}</code></div>` +
          codeForm('');
        wire(card, data.id, sb, done, onSignOut);
      })();
    });
  }

  window.StaffMFA = { ensure };
})();
