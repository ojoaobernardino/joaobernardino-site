/* Validador de e-mail dos formulários do site (newsletter em todas as páginas).
   Barra e-mail sem formato, domínio digitado errado (gmial, hotmal, gmail.co...),
   e-mail descartável e cadastro de teste. Quando reconhece o erro, sugere o certo.
   Uso: var r = validaEmail(valor); r.ok, r.msg, r.sugestao */
(function () {
  // domínios mais usados no Brasil: o que for "quase isso" vira sugestão
  var CERTOS = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'yahoo.com.br', 'icloud.com',
    'live.com', 'msn.com', 'uol.com.br', 'bol.com.br', 'terra.com.br', 'globo.com', 'ig.com.br', 'me.com', 'protonmail.com'];
  // erros de digitação que a distância de edição não pega sozinha
  var FIXOS = {
    'gmail.com.br': 'gmail.com', 'gmail.co': 'gmail.com', 'gmail.cm': 'gmail.com', 'gmail.om': 'gmail.com',
    'gmail.con': 'gmail.com', 'gmail.comm': 'gmail.com', 'gmail.coom': 'gmail.com', 'gmail.cpm': 'gmail.com',
    'gmail.combr': 'gmail.com', 'gmail': 'gmail.com', 'gmailcom': 'gmail.com', 'gmail.c': 'gmail.com',
    'hotmail.com.br': 'hotmail.com', 'hotmail.co': 'hotmail.com', 'hotmail.con': 'hotmail.com', 'hotmail': 'hotmail.com',
    'outlook.com.br': 'outlook.com', 'outlook.co': 'outlook.com', 'outlook.con': 'outlook.com', 'outlook': 'outlook.com',
    'yahoo.co': 'yahoo.com', 'yahoo.con': 'yahoo.com', 'yahoo.combr': 'yahoo.com.br', 'yahoo': 'yahoo.com',
    'icloud.co': 'icloud.com', 'icloud.con': 'icloud.com', 'icloud': 'icloud.com'
  };
  var DESCARTAVEIS = ['mailinator.com', 'yopmail.com', 'guerrillamail.com', 'sharklasers.com', '10minutemail.com',
    'temp-mail.org', 'tempmail.com', 'tempmail.net', 'trashmail.com', 'getnada.com', 'dispostable.com',
    'maildrop.cc', 'mintemail.com', 'fakeinbox.com', 'throwawaymail.com', 'emailondeck.com', 'mohmal.com', 'tempr.email'];
  var TESTE = /^(teste?|test|asdf+|qwe(rty)?|abc|aaa+|xxx+|nome|email|seuemail|seu\.?email|fulano|exemplo|example|naotenho|nao|none|null)\d*$/;

  function dist(a, b) { // distância de edição (com troca de letras vizinhas)
    var m = a.length, n = b.length, d = [], i, j;
    for (i = 0; i <= m; i++) d[i] = [i];
    for (j = 0; j <= n; j++) d[0][j] = j;
    for (i = 1; i <= m; i++) for (j = 1; j <= n; j++)
    {
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1); // letras trocadas (gmial)
    }
    return d[m][n];
  }

  window.validaEmail = function (valor) {
    var v = String(valor || '').trim().toLowerCase().replace(/\s+/g, '');
    if (!v) return { ok: false, msg: 'Digite o seu e-mail.' };
    var p = v.split('@');
    if (p.length !== 2 || !p[0] || !p[1]) return { ok: false, msg: 'Confira o e-mail: falta o @ ou o que vem depois dele.' };
    var usuario = p[0], dominio = p[1].replace(/\.+$/, '');
    if (!/^[a-z0-9._%+-]+$/.test(usuario) || /^\.|\.\.|\.$/.test(usuario)) return { ok: false, msg: 'Confira o e-mail: tem algum caractere que não vale antes do @.' };
    var fixo = FIXOS[dominio];
    if (fixo) return { ok: false, msg: 'Você quis dizer ' + usuario + '@' + fixo + '?', sugestao: usuario + '@' + fixo };
    if (!/^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/.test(dominio)) return { ok: false, msg: 'Confira o final do e-mail (ex.: @gmail.com).' };
    if (DESCARTAVEIS.indexOf(dominio) > -1) return { ok: false, msg: 'Use um e-mail que você lê de verdade. E-mail temporário não recebe o conteúdo.' };
    if (TESTE.test(usuario) && CERTOS.indexOf(dominio) > -1) return { ok: false, msg: 'Parece um e-mail de teste. Use o seu e-mail de verdade.' };
    if (CERTOS.indexOf(dominio) === -1) {
      var melhor = null, menor = 3;
      for (var k = 0; k < CERTOS.length; k++) { var dd = dist(dominio, CERTOS[k]); if (dd < menor) { menor = dd; melhor = CERTOS[k]; } }
      if (melhor && menor <= (melhor.length >= 10 ? 2 : 1)) return { ok: false, msg: 'Você quis dizer ' + usuario + '@' + melhor + '?', sugestao: usuario + '@' + melhor };
    }
    return { ok: true, email: usuario + '@' + dominio };
  };

  // liga em todo formulário com campo de e-mail: mostra o aviso e, se houver sugestão, um clique corrige
  window.checaEmailNoForm = function (input, saida) {
    var r = window.validaEmail(input.value);
    // sugestão de domínio pode errar (e-mail de empresa): se a pessoa enviar de novo o mesmo e-mail, aceita
    if (!r.ok && r.sugestao && input.getAttribute('data-avisado') === input.value.trim().toLowerCase()) {
      r = { ok: true, email: input.value.trim().toLowerCase() };
    }
    if (r.ok) { input.value = r.email; input.removeAttribute('aria-invalid'); return true; }
    input.setAttribute('aria-invalid', 'true');
    if (r.sugestao) input.setAttribute('data-avisado', input.value.trim().toLowerCase());
    saida.hidden = false;
    saida.textContent = '';
    saida.appendChild(document.createTextNode(r.msg + (r.sugestao ? ' Se o seu e-mail é esse mesmo, é só enviar de novo.' : '')));
    if (r.sugestao) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'email-fix'; b.textContent = 'Corrigir';
      b.addEventListener('click', function () { input.value = r.sugestao; input.removeAttribute('aria-invalid'); saida.hidden = true; input.focus(); });
      saida.appendChild(document.createTextNode(' ')); saida.appendChild(b);
    }
    input.focus();
    return false;
  };
})();
