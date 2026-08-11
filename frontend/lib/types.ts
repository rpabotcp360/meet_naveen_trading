export interface Signal {
  id: number;
  symbol: string;
  company_name?: string;
  direction: "BUY" | "SELL";
  entry: number;
  stop_loss: number;
  target_1: number;
  target_2: number;
  target_3: number;
  buy_score: number;
  sell_score: number;
  rvol: number;
  htf_direction: string;
  universe_source: string;
  candle_timestamp_utc?: string;
  generated_at_utc: string;
  telegram_sent?: boolean;
  archived?: boolean;
  is_realtime?: boolean;
  quantity?: number;
  capital_used?: number;
  outcome?: string;
}

export interface ScannerRow {
  instrument_key: string;
  symbol: string;
  company_name: string;
  ltp: number;
  change_pct: number;
  rvol: number;
  buy_score: number;
  sell_score: number;
  ema_trend: string;
  vwap_state: string;
  supertrend: string;
  rsi: number;
  macd_state: string;
  htf: string;
  scanner_state: string;
  source: string;
}

export interface SystemStatus {
  backend: string;
  upstox_rest: string;
  upstox_websocket: string;
  telegram: string;
  scanner_state: string;
  subscribed_instruments: number;
  uptime_seconds: number;
  last_error: string;
}

export interface WatchlistItem {
  id: number;
  instrument_key: string;
  trading_symbol: string;
  company_name: string;
  enabled: boolean;
  pinned: boolean;
  segment_id?: number | null;
}

export interface Segment {
  id: number;
  name: string;
}

export interface WsMessage {
  type: string;
  data: unknown;
}
