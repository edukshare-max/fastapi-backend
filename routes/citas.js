const express = require('express');
const router = express.Router();
const { findCitasByMatricula, cleanCosmosDocument } = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

/**
 * GET /me/citas
 * Obtener todas las citas del usuario autenticado
 */
router.get('/citas', authenticateToken, async (req, res) => {
  try {
    const { matricula } = req.user;

    if (!matricula) {
      return res.status(400).json({
        success: false,
        message: 'Matrícula no encontrada en token'
      });
    }

    // Buscar citas en SASU
    const citas = await findCitasByMatricula(matricula);

    // Limpiar datos técnicos de Cosmos DB de todas las citas
    const citasLimpias = citas.map(cita => cleanCosmosDocument(cita));

    // Log exitoso
    console.log(`📅 ${citasLimpias.length} citas encontradas para matrícula: ${matricula}`);

    // Respuesta exitosa
    res.json({
      success: true,
      data: citasLimpias,
      count: citasLimpias.length
    });

  } catch (error) {
    console.error('❌ Error obteniendo citas:', error);
    res.status(500).json({
      success: false,
      message: 'Error interno del servidor'
    });
  }
});

/**
 * GET /me/citas/:id
 * Obtener una cita específica por ID (opcional, para futuras funcionalidades)
 */
router.get('/citas/:id', authenticateToken, async (req, res) => {
  try {
    const { matricula } = req.user;
    const { id } = req.params;

    if (!matricula) {
      return res.status(400).json({
        success: false,
        message: 'Matrícula no encontrada en token'
      });
    }

    // Buscar todas las citas del usuario
    const citas = await findCitasByMatricula(matricula);
    
    // Buscar la cita específica
    const cita = citas.find(c => c.id === id);

    if (!cita) {
      return res.status(404).json({
        success: false,
        message: 'Cita no encontrada'
      });
    }

    // Limpiar datos técnicos de Cosmos DB
    const citaLimpia = cleanCosmosDocument(cita);

    // Log exitoso
    console.log(`📋 Cita ${id} solicitada para matrícula: ${matricula}`);

    // Respuesta exitosa
    res.json({
      success: true,
      data: citaLimpia
    });

  } catch (error) {
    console.error('❌ Error obteniendo cita específica:', error);
    res.status(500).json({
      success: false,
      message: 'Error interno del servidor'
    });
  }
});

module.exports = router;