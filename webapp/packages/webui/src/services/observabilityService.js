// webapp/packages/webui/src/services/observabilityService.js
import apiClient from './apiClient';
import authService from './authService';

class ObservabilityService {
  /**
   * Logs an event by sending it to the backend.
   * This is a "fire-and-forget" operation from the UI's perspective.
   * @param {object} logData
   * @param {string} logData.eventType - The type of event (e.g., 'user-action', 'error', 'navigation').
   * @param {string} logData.message - A descriptive message for the log.
   * @param {string} [logData.level='INFO'] - The log level ('INFO', 'WARN', 'ERROR').
   * @param {object} [logData.metadata={}] - Any additional contextual data.
   */
  log({ eventType, message, level = 'INFO', metadata = {} }) {
    const payload = {
      eventType,
      message,
      level,
      metadata,
    };

    // Use apiClient to send the log without awaiting the response.
    // Error handling is done inside apiClient and will log to console if it fails.
    apiClient.post('/log/client', payload).catch(error => {
      console.error('Failed to send client log to backend:', error);
    });
  }

  /**
   * A specific helper for logging errors.
   * @param {Error} error - The error object.
   * @param {object} [context={}] - Additional context about where the error occurred.
   */
  logError(error, context = {}) {
    this.log({
      eventType: 'error',
      message: error.message,
      level: 'ERROR',
      metadata: {
        ...context,
        stack: error.stack,
        name: error.name,
      },
    });
  }
}

export default new ObservabilityService();