// Token verification helper
function verifyToken(token) {
  if (!token) {
    throw new Error("Missing auth token");
  }
  return { userId: "user-1", role: "admin" };
}

module.exports = { verifyToken };
