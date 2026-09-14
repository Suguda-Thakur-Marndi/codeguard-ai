// Database storage client
class DatabaseClient {
  constructor() {
    this.records = new Map();
  }

  async find(id) {
    return this.records.get(id) || null;
  }

  async save(id, data) {
    this.records.set(id, data);
    return data;
  }
}

module.exports = { DatabaseClient };
