const express = require('express');
const router = express.Router();
const { findCarnetByMatricula, cleanCosmosDocument } = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

/**
 * GET /me/carnet
 * Obtener información completa del carnet del usuario autenticado
 */
router.get('/carnet', authenticateToken, async (req, res) => {
  try {
    const { matricula } = req.user;

    if (!matricula) {
      return res.status(400).json({
        success: false,
        message: 'Matrícula no encontrada en token'
      });
    }

    // Buscar carnet en SASU
    const carnet = await findCarnetByMatricula(matricula);

    if (!carnet) {
      return res.status(404).json({
        success: false,
        message: 'Carnet no encontrado'
      });
    }

    // Limpiar datos técnicos de Cosmos DB
    const carnetLimpio = cleanCosmosDocument(carnet);

    // Log exitoso
    console.log(`📋 Carnet solicitado para matrícula: ${matricula}`);

    // Respuesta exitosa
    res.json({
      success: true,
      data: carnetLimpio
    });

  } catch (error) {
    console.error('❌ Error obteniendo carnet:', error);
    res.status(500).json({
      success: false,
      message: 'Error interno del servidor'
    });
  }
});

module.exports = router;