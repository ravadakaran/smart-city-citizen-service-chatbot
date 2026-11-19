import axios from 'axios';
import { CivicTicket } from './types';

const api = axios.create({
  baseURL: '/api/v1',
});

export async function sendChatMessage(sessionId: string, message: string) {
  const { data } = await api.post('/chat/message', {
    session_id: sessionId,
    message,
  });
  return data;
}

export async function submitGrievance(formData: FormData) {
  const { data } = await api.post('/grievances/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function fetchAdminHeatmap(token: string): Promise<CivicTicket[]> {
  const { data } = await api.get('/admin/heatmap', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return data.tickets;
}

export async function updateTicketStatus(
  token: string,
  ticketId: string,
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED'
) {
  const { data } = await api.patch(
    `/admin/tickets/${ticketId}`,
    { status },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return data;
}
