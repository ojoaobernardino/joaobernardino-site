const AC_URL  = 'https://vendraminijoao.api-us1.com';
const AC_KEY  = '3a78b93545a9cbb6bc48e8781b8cf50ea4a6b962b7a2bb89cab36f2aabe1032eb39664a6';
const LIST_ID = 4;

const VOXUY_URL   = 'https://sistema.voxuy.com/api/b23a12fa-f4e2-4324-841c-433687aa86ae/webhooks/voxuy/transaction';
const VOXUY_TOKEN = '0e7d0660-a981-4973-b8b5-657ae28cd559';
const VOXUY_PLAN  = '1156467'; // Funil API "Carrinho Abandonado - Zero Nóia"

/* Produtos que disparam carrinho abandonado no WhatsApp */
const VOXUY_PRODUTOS = ['zero-noia', 'zero-noia-50off', 'zero-noia-70off'];

/* Tag AC por produto */
const TAG_MAP = {
  'zero-noia':       'carrinho-abandonado-zeronoia',
  'zero-noia-50off': 'carrinho-abandonado-zeronoia',
  'zero-noia-70off': 'carrinho-abandonado-zeronoia',
  '21-leis':         'interesse:21-leis'
};

async function applyTag(contactId, tagName) {
  const tagRes = await fetch(`${AC_URL}/api/3/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
    body: JSON.stringify({ tag: { tag: tagName, tagType: 'contact', description: '' } })
  });
  const tagData = await tagRes.json();
  const tagId = tagData.tag?.id;
  if (!tagId) return;
  await fetch(`${AC_URL}/api/3/contactTags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
    body: JSON.stringify({ contactTag: { contact: contactId, tag: tagId } })
  });
}

async function triggerVoxuy(nome, email, wpp) {
  const digits = wpp.replace(/\D/g, '');
  const phone  = digits.startsWith('55') ? `+${digits}` : `+55${digits}`;
  if (phone.length < 13) return;

  await fetch(VOXUY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      apiToken:          VOXUY_TOKEN,
      planId:            VOXUY_PLAN,
      clientPhoneNumber: phone,
      name:              nome,
      email:             email,
      status:            80 // Abandoned Cart
    })
  });
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const headers = {
    'Access-Control-Allow-Origin': 'https://joaobernardino.com.br',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
  };

  try {
    const { nome, email, wpp, produto } = JSON.parse(event.body);

    if (!nome || !email) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Campos obrigatórios ausentes' }) };
    }

    // 1. Criar/atualizar contato no AC
    const contactRes = await fetch(`${AC_URL}/api/3/contacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
      body: JSON.stringify({ contact: { firstName: nome, email, phone: wpp || '' } })
    });
    const contactData = await contactRes.json();
    const contactId = contactData.contact?.id;

    if (!contactId) {
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Erro ao criar contato', detail: contactData }) };
    }

    // 2. Inscrever na lista
    await fetch(`${AC_URL}/api/3/contactLists`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
      body: JSON.stringify({ contactList: { list: LIST_ID, contact: contactId, status: 1 } })
    });

    // 3. Aplicar tag AC (dispara automação de 5 emails)
    const tagName = TAG_MAP[produto];
    if (tagName) {
      await applyTag(contactId, tagName).catch(() => {});
    }

    // 4. Disparar WhatsApp carrinho abandonado via Voxuy (só Zero Nóia)
    if (wpp && VOXUY_PRODUTOS.includes(produto)) {
      await triggerVoxuy(nome, email, wpp).catch(() => {});
    }

    return { statusCode: 200, headers, body: JSON.stringify({ success: true, contactId }) };

  } catch (err) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};
