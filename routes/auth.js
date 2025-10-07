const express = require('express');
const router = express.Router();
const { findCarnetByEmailAndMatricula } = require('../config/database');
const { generateToken } = require('../middleware/auth');

/**
 * POST /auth/login
 * Autenticar usuario con correo y matrícula
 */
router.post('/login', async (req, res) => {
  try {
    const { email, matricula } = req.body;

    // Validar que se envíen ambos campos
    if (!email || !matricula) {
      return res.status(400).json({
        success: false,
        message: 'Email y matrícula son requeridos'
      });
    }

    // Buscar usuario en SASU
    const carnet = await findCarnetByEmailAndMatricula(email, matricula);

    if (!carnet) {
      return res.status(401).json({
        success: false,
        message: 'Credenciales incorrectas'
      });
    }

    // Generar JWT token
    const token = generateToken(carnet.matricula);

    // Log exitoso (sin datos sensibles)
    console.log(`✅ Login exitoso para matrícula: ${carnet.matricula}`);

    // Respuesta exitosa
    res.json({
      success: true,
      token: token,
      matricula: carnet.matricula,
      message: 'Login exitoso'
    });

  } catch (error) {
    console.error('❌ Error en login:', error);
    res.status(500).json({
      success: false,
      message: 'Error interno del servidor'
    });
  }
});

/**
 * POST /auth/verify
 * Verificar si un token es válido (opcional, para debugging)
 */
router.post('/verify', async (req, res) => {
  try {
    const { token } = req.body;

    if (!token) {
      return res.status(400).json({
        success: false,
        message: 'Token requerido'
      });
    }

    const { verifyToken } = require('../middleware/auth');
    const decoded = verifyToken(token);

    if (!decoded) {
      return res.status(401).json({
        success: false,
        message: 'Token inválido'
      });
    }

    res.json({
      success: true,
      valid: true,
      matricula: decoded.matricula,
      iat: decoded.iat,
      exp: decoded.exp
    });

  } catch (error) {
    console.error('❌ Error verificando token:', error);
    res.status(500).json({
      success: false,
      message: 'Error interno del servidor'
    });
  }
});

module.exports = router;