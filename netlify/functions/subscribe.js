const AC_URL = 'https://vendraminijoao.api-us1.com';
const AC_KEY = '3a78b93545a9cbb6bc48e8781b8cf50ea4a6b962b7a2bb89cab36f2aabe1032eb39664a6';
const LIST_ID = 4;

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
    const { nome, email, wpp } = JSON.parse(event.body);

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
