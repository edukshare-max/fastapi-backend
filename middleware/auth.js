const jwt = require('jsonwebtoken');

/**
 * Middleware para verificar JWT token
 * @param {Object} req - Request object
 * @param {Object} res - Response object
 * @param {Function} next - Next middleware function
 */
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({
      success: false,
      message: 'Token de acceso requerido'
    });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      console.log('Error verificando token:', err.message);
      return res.status(403).json({
        success: false,
        message: 'Token inválido o expirado'
      });
    }

    // Agregar información del usuario al request
    req.user = user;
    next();
  });
}

/**
 * Generar JWT token
 * @param {string} matricula - Matrícula del usuario
 * @returns {string} - JWT token
 */
function generateToken(matricula) {
  const payload = {
    matricula: matricula,
    iat: Math.floor(Date.now() / 1000)
  };

  return jwt.sign(payload, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || '7d'
  });
}

/**
 * Verificar token sin middleware (para uso directo)
 * @param {string} token - JWT token
 * @returns {Object|null} - Payload del token o null si es inválido
 */
function verifyToken(token) {
  try {
    return jwt.verify(token, process.env.JWT_SECRET);
  } catch (error) {
    return null;
  }
}

module.exports = {
  authenticateToken,
  generateToken,
  verifyToken
};