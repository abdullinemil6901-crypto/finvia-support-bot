/**
 * Supabase Edge Function: check-stale-tickets
 *
 * Проверяет тикеты старше 12 минут и отправляет алерт.
 * Вызывается через pg_cron каждые 2 минуты.
 *
 * Требует переменные окружения:
 * - SUPABASE_URL
 * - SUPABASE_SERVICE_ROLE_KEY
 * - BOT_TOKEN
 * - SUPPORT_CHAT_ID
 */

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const BOT_TOKEN = Deno.env.get('BOT_TOKEN');
const SUPPORT_CHAT_ID = Deno.env.get('SUPPORT_CHAT_ID');

interface Ticket {
  id: number;
  label: string;
  trader_username: string;
  created_at: string;
  trader_chat_id: number | null;
}

async function supabaseQuery(query: string): Promise<any[]> {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/exec_sql`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SUPABASE_SERVICE_ROLE_KEY,
      'Authorization': `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    },
    body: JSON.stringify({ query }),
  });
  return response.json();
}

async function getStaleTickets(): Promise<Ticket[]> {
  const response = await fetch(
    `${SUPABASE_URL}/rest/v1/tickets?status=eq.open&alert_sent=eq.false&created_at=lt.now()%20-%20interval%20%2712%20minutes%27&select=id,label,trader_username,created_at,trader_chat_id`,
    {
      headers: {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
      },
    }
  );
  return response.json();
}

async function markAlertSent(ticketId: number): Promise<void> {
  await fetch(
    `${SUPABASE_URL}/rest/v1/tickets?id=eq.${ticketId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify({ alert_sent: true }),
    }
  );
}

async function sendTelegramMessage(chatId: string, text: string): Promise<void> {
  if (!BOT_TOKEN) {
    console.log('BOT_TOKEN not set, skipping Telegram message');
    return;
  }

  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'HTML',
    }),
  });
}

Deno.serve(async (req) => {
  console.log('Checking for stale tickets...');

  try {
    const staleTickets = await getStaleTickets();
    console.log(`Found ${staleTickets.length} stale tickets`);

    for (const ticket of staleTickets) {
      const createdDate = new Date(ticket.created_at);
      const minutesAgo = Math.floor((Date.now() - createdDate.getTime()) / 60000);

      // Формируем сообщение для саппорт-чата
      const supportMessage = `⚠️ <b>Тикет #${ticket.id} не взят!</b>\n\n📋 ${ticket.label}\n👤 @${ticket.trader_username || 'unknown'}\n⏱️ ${minutesAgo} мин`;

      // Отправляем в саппорт-чат
      if (SUPPORT_CHAT_ID) {
        await sendTelegramMessage(SUPPORT_CHAT_ID, supportMessage);
      }

      // Уведомляем трейдера
      if (ticket.trader_chat_id) {
        const traderMessage = `⏰ <b>Напоминание по заявке #${ticket.id}</b>\n\nВаша заявка "${ticket.label}" ещё не взята в работу.\n\nПожалуйста, ожидайте — саппорт скоро ответит.`;
        await sendTelegramMessage(String(ticket.trader_chat_id), traderMessage);
      }

      // Отмечаем что алерт отправлен
      await markAlertSent(ticket.id);
      console.log(`Alert sent for ticket #${ticket.id}`);
    }

    return new Response(
      JSON.stringify({ success: true, alerts_sent: staleTickets.length }),
      { headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error:', error);
    return new Response(
      JSON.stringify({ success: false, error: String(error) }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
});
