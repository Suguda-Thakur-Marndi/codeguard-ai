import { IPaymentGateway } from '../interfaces/IPaymentGateway';
import { PaymentTransaction, RefundResponse } from '../types/payment';

export class StripeGateway implements IPaymentGateway {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async charge(transaction: PaymentTransaction): Promise<boolean> {
    return true;
  }

  async refund(transactionId: string, amount: number): Promise<RefundResponse> {
    return {
      transactionId,
      refundedAmount: amount,
      status: 'SUCCESS',
    };
  }
}
