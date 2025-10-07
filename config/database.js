const { CosmosClient } = require('@azure/cosmos');

let cosmosClient;
let database;
let carnetsContainer;
let citasContainer;

/**
 * Inicializar conexión a Azure Cosmos DB
 */
async function connectToCosmosDB() {
  try {
    const endpoint = process.env.COSMOS_ENDPOINT;
    const key = process.env.COSMOS_KEY;
    const databaseName = process.env.COSMOS_DATABASE || 'SASU';
    const carnetsContainerName = process.env.COSMOS_CONTAINER_CARNETS || 'carnets_id';
    const citasContainerName = process.env.COSMOS_CONTAINER_CITAS || 'cita_id';

    if (!endpoint || !key) {
      throw new Error('COSMOS_ENDPOINT y COSMOS_KEY son requeridos en variables de entorno');
    }

    // Crear cliente de Cosmos DB
    cosmosClient = new CosmosClient({
      endpoint,
      key,
      userAgentSuffix: 'CarnetDigitalUAGro'
    });

    // Conectar a la base de datos
    database = cosmosClient.database(databaseName);
    
    // Verificar que la base de datos existe
    const { database: dbResponse } = await database.read();
    console.log(`📚 Conectado a base de datos: ${dbResponse.id}`);

    // Conectar a contenedores
    carnetsContainer = database.container(carnetsContainerName);
    citasContainer = database.container(citasContainerName);

    // Verificar que los contenedores existen
    const { container: carnetsResponse } = await carnetsContainer.read();
    const { container: citasResponse } = await citasContainer.read();
    
    console.log(`📦 Contenedor carnets: ${carnetsResponse.id}`);
    console.log(`📦 Contenedor citas: ${citasResponse.id}`);

    return true;
  } catch (error) {
    console.error('❌ Error conectando a Cosmos DB:', error.message);
    throw error;
  }
}

/**
 * Buscar carnet por correo y matrícula
 * @param {string} correo - Email del usuario
 * @param {string} matricula - Matrícula del usuario
 * @returns {Object|null} - Documento del carnet o null si no existe
 */
async function findCarnetByEmailAndMatricula(correo, matricula) {
  try {
    const querySpec = {
      query: 'SELECT * FROM c WHERE c.correo = @correo AND c.matricula = @matricula',
      parameters: [
        { name: '@correo', value: correo },
        { name: '@matricula', value: matricula }
      ]
    };

    const { resources } = await carnetsContainer.items.query(querySpec).fetchAll();
    return resources.length > 0 ? resources[0] : null;
  } catch (error) {
    console.error('Error buscando carnet:', error);
    throw error;
  }
}

/**
 * Buscar carnet por matrícula
 * @param {string} matricula - Matrícula del usuario
 * @returns {Object|null} - Documento del carnet o null si no existe
 */
async function findCarnetByMatricula(matricula) {
  try {
    const querySpec = {
      query: 'SELECT * FROM c WHERE c.matricula = @matricula',
      parameters: [
        { name: '@matricula', value: matricula }
      ]
    };

    const { resources } = await carnetsContainer.items.query(querySpec).fetchAll();
    return resources.length > 0 ? resources[0] : null;
  } catch (error) {
    console.error('Error buscando carnet por matrícula:', error);
    throw error;
  }
}

/**
 * Buscar citas por matrícula
 * @param {string} matricula - Matrícula del usuario
 * @returns {Array} - Array de citas del usuario
 */
async function findCitasByMatricula(matricula) {
  try {
    const querySpec = {
      query: 'SELECT * FROM c WHERE c.matricula = @matricula ORDER BY c.inicio DESC',
      parameters: [
        { name: '@matricula', value: matricula }
      ]
    };

    const { resources } = await citasContainer.items.query(querySpec).fetchAll();
    return resources;
  } catch (error) {
    console.error('Error buscando citas:', error);
    throw error;
  }
}

/**
 * Limpiar datos del documento eliminando campos técnicos de Cosmos DB
 * @param {Object} documento - Documento de Cosmos DB
 * @returns {Object} - Documento limpio sin campos técnicos
 */
function cleanCosmosDocument(documento) {
  if (!documento) return null;

  // Crear copia del documento
  const cleanDoc = { ...documento };

  // Eliminar campos técnicos de Cosmos DB
  delete cleanDoc._rid;
  delete cleanDoc._self;
  delete cleanDoc._etag;
  delete cleanDoc._attachments;
  delete cleanDoc._ts;

  return cleanDoc;
}

module.exports = {
  connectToCosmosDB,
  findCarnetByEmailAndMatricula,
  findCarnetByMatricula,
  findCitasByMatricula,
  cleanCosmosDocument,
  // Exportar clientes para uso directo si es necesario
  getCosmosClient: () => cosmosClient,
  getDatabase: () => database,
  getCarnetsContainer: () => carnetsContainer,
  getCitasContainer: () => citasContainer
};