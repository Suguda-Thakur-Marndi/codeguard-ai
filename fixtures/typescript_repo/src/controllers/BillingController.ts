import { IPaymentGateway } from '../interfaces/IPaymentGateway';
import { RefundResponse } from '../types/payment';

export class BillingController {
  private gateway: IPaymentGateway;

  constructor(gateway: IPaymentGateway) {
    this.gateway = gateway;
  }

  async handleRefund(id: string, amount: number): Promise<RefundResponse> {
    return this.gateway.refund(id, amount);
  }
}
