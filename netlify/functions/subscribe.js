const AC_URL = 'https://vendraminijoao.api-us1.com';
const AC_KEY = '3a78b93545a9cbb6bc48e8781b8cf50ea4a6b962b7a2bb89cab36f2aabe1032eb39664a6';
const LIST_ID = 4;

/* Mapeia dest → tag no AC (dispara automação de carrinho abandonado) */
const TAG_MAP = {
  'zero-noia':       'carrinho-abandonado-zeronoia',
  'zero-noia-50off': 'carrinho-abandonado-zeronoia',
  'zero-noia-70off': 'carrinho-abandonado-zeronoia',
  '21-leis':         'interesse:21-leis'
};

async function applyTag(contactId, tagName) {
  /* 1. Cria/recupera a tag */
  const tagRes = await fetch(`${AC_URL}/api/3/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
    body: JSON.stringify({ tag: { tag: tagName, tagType: 'contact', description: '' } })
  });
  const tagData = await tagRes.json();
  const tagId = tagData.tag?.id;
  if (!tagId) return;

  /* 2. Aplica ao contato */
  await fetch(`${AC_URL}/api/3/contactTags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
    body: JSON.stringify({ contactTag: { contact: contactId, tag: tagId } })
  });
}

exports.handler = async function(event) {
  // Só aceita POST
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  // CORS — permite chamadas do seu site
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

    // 1. Criar/atualizar contato
    const contactRes = await fetch(`${AC_URL}/api/3/contacts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Api-Token': AC_KEY
      },
      body: JSON.stringify({
        contact: {
          firstName: nome,
          email: email,
          phone: wpp || ''
        }
      })
    });

    const contactData = await contactRes.json();
    const contactId = contactData.contact?.id;

    if (!contactId) {
      return { statusCode: 500, headers, body: JSON.stringify({ error: 'Erro ao criar contato', detail: contactData }) };
    }

    // 2. Inscrever na lista
    await fetch(`${AC_URL}/api/3/contactLists`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Api-Token': AC_KEY
      },
      body: JSON.stringify({
        contactList: {
          list: LIST_ID,
          contact: contactId,
          status: 1
        }
      })
    });

    /* 3. Aplicar tag de interesse se vier da máscara */
    const tagName = TAG_MAP[produto];
    if (tagName) {
      await applyTag(contactId, tagName).catch(() => {}); // silencia erro de tag
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ success: true, contactId })
    };

  } catch (err) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: err.message })
    };
  }
};
