export interface ChatMessage {
  id: string;
  sender: 'citizen' | 'bot';
  text: string;
  citations?: string[];
  grounded?: boolean;
  intent?: string;
  timestamp: string;
}

export interface CivicTicket {
  ticket_id: string;
  department_code: 'ROADS' | 'WASTE' | 'WATER' | 'EMERGENCY';
  issue_subcategory: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  upvote_count: number;
  lat: number;
  lon: number;
  sla_deadline: string;
  created_at: string;
}
