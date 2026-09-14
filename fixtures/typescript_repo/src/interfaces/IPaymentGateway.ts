import { PaymentTransaction, RefundResponse } from '../types/payment';

export interface IPaymentGateway {
  charge(transaction: PaymentTransaction): Promise<boolean>;
  refund(transactionId: string, amount: number): Promise<RefundResponse>;
}
