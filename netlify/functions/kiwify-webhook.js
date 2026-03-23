const AC_URL = 'https://vendraminijoao.api-us1.com';
const AC_KEY = '3a78b93545a9cbb6bc48e8781b8cf50ea4a6b962b7a2bb89cab36f2aabe1032eb39664a6';

async function acGet(path) {
  return fetch(`${AC_URL}/api/3${path}`, {
    headers: { 'Api-Token': AC_KEY }
  }).then(r => r.json());
}

async function acPost(path, body) {
  return fetch(`${AC_URL}/api/3${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Api-Token': AC_KEY },
    body: JSON.stringify(body)
  }).then(r => r.json());
}

async function removeTag(contactId, tagName) {
  const tags = await acGet('/tags');
  const tagId = tags.tags?.find(t => t.tag === tagName)?.id;
  if (!tagId) return;
  const ct = await acGet(`/contactTags?contact=${contactId}&tag=${tagId}`);
  const ctId = ct.contactTags?.[0]?.id;
  if (ctId) {
    await fetch(`${AC_URL}/api/3/contactTags/${ctId}`, {
      method: 'DELETE',
      headers: { 'Api-Token': AC_KEY }
    });
  }
}

async function addTag(contactId, tagName) {
  const res = await acPost('/tags', { tag: { tag: tagName, tagType: 'contact', description: '' } });
  const tagId = res.tag?.id;
  if (!tagId) return;
  await acPost('/contactTags', { contactTag: { contact: contactId, tag: tagId } });
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const payload = JSON.parse(event.body);

    // Aceita apenas vendas aprovadas
    const status = payload.order?.status || payload.status;
    if (status !== 'paid' && status !== 'approved') {
      return { statusCode: 200, body: JSON.stringify({ ignored: true, status }) };
    }

    const email = payload.customer?.email || payload.email;
    if (!email) {
      return { statusCode: 400, body: JSON.stringify({ error: 'Email não encontrado' }) };
    }

    // Busca contato no AC pelo email
    const data = await acGet(`/contacts?email=${encodeURIComponent(email)}`);
    const contact = data.contacts?.[0];

    if (contact) {
      await removeTag(contact.id, 'carrinho-abandonado-zeronoia');
      await addTag(contact.id, 'comprou-zeronoia');
    }

    return { statusCode: 200, body: JSON.stringify({ success: true, email }) };

  } catch (err) {
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
};
