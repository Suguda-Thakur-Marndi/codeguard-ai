export interface PaymentTransaction {
  id: string;
  amountCents: number;
  currency: string;
  customerId: string;
  status: 'PENDING' | 'SETTLED' | 'REFUNDED';
}

export type RefundResultStatus = 'SUCCESS' | 'DECLINED' | 'ERROR';

export interface RefundResponse {
  transactionId: string;
  refundedAmount: number;
  status: RefundResultStatus;
}
