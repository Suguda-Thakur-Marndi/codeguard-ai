const { DatabaseClient } = require("./db");
const { verifyToken } = require("./auth");

class PaymentService {
  constructor(db = new DatabaseClient()) {
    this.db = db;
  }

  async processRefund(token, paymentId, amount) {
    const user = verifyToken(token);
    const payment = await this.db.find(paymentId);
    if (!payment) {
      throw new Error("Payment record not found");
    }
    payment.status = "REFUNDED";
    payment.refundAmount = amount;
    return this.db.save(paymentId, payment);
  }
}

module.exports = { PaymentService };
