/**
 * Frontend JavaScript per PSTT Tool
 */

class PSITTool {
    constructor() {
        this.currentConnection = null;
        this.currentQuery = null;
        this.queries = [];
        this.lastResults = null;
        this.filters = {};
        this.sorting = {};
        
        this.initializeEventListeners();
        this.loadQueries();
        this.loadConnectionStatus();
    }
    
    initializeEventListeners() {
        // Connection selector
        document.getElementById('connectionSelector').addEventListener('change', (e) => {
            this.switchConnection(e.target.value);
        });
        
        // Test connection button
        document.getElementById('testConnectionBtn').addEventListener('click', () => {
            this.testConnection();
        });
        
        // Execute query button
        document.getElementById('executeQueryBtn').addEventListener('click', () => {
            this.executeQuery();
        });
        
        // Export buttons
        document.getElementById('exportExcelBtn').addEventListener('click', () => {
            this.exportResults('excel');
        });
        
        document.getElementById('exportCsvBtn').addEventListener('click', () => {
            this.exportResults('csv');
        });
    }
    
    async loadQueries() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/queries/');
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Errore nel caricamento delle query');
            }
            
            this.queries = data.queries;
            this.renderQueryList();
            
        } catch (error) {
            console.error('Errore nel caricamento delle query:', error);
            this.showError('Errore nel caricamento delle query: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    filterQueriesByConnection() {
        if (!this.currentConnection) {
            return this.queries;
        }
        
        // Estrae il codice database dal nome connessione (es. A00-CDG-Collaudo -> CDG)
        let dbCode = '';
        const connectionParts = this.currentConnection.split('-');
        if (connectionParts.length >= 2) {
            dbCode = connectionParts[1]; // CDG, BOSC, TT2_UFFICIO, etc.
        }
        
        console.log(`Filtering queries for connection: ${this.currentConnection}, dbCode: ${dbCode}`);
        
        // Filtra le query che iniziano con lo stesso codice database
        const filteredQueries = this.queries.filter(query => {
            const queryPrefix = query.filename.split('-')[0]; // Parte prima del primo '-'
            const isMatch = queryPrefix === dbCode || 
                           queryPrefix.includes(dbCode) || 
                           (dbCode === 'TT2_UFFICIO' && queryPrefix === 'TT2_UFFICIO');
            
            if (isMatch) {
                console.log(`Matched query: ${query.filename}`);
            }
            
            return isMatch;
        });
        
        console.log(`Filtered ${filteredQueries.length} queries from ${this.queries.length} total`);
        return filteredQueries;
    }

    renderQueryList() {
        const queryList = document.getElementById('queryList');
        queryList.innerHTML = '';
        // Filtra le query in base alla connessione corrente
        const filteredQueries = this.filterQueriesByConnection();
        // Ordina alfabeticamente per gruppo+nome
        filteredQueries.sort((a, b) => {
            const nameA = this._getQueryDisplayName(a.filename).toLowerCase();
            const nameB = this._getQueryDisplayName(b.filename).toLowerCase();
            return nameA.localeCompare(nameB);
        });
        if (filteredQueries.length === 0) {
            queryList.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <p>Nessuna query disponibile per la connessione corrente</p>
                    <p class="text-sm">Seleziona una connessione appropriata</p>
                </div>
            `;
            return;
        }
        filteredQueries.forEach(query => {
            const queryItem = document.createElement('div');
            queryItem.className = 'query-item';
            // Evidenzia la query selezionata
            if (this.currentQuery && this.currentQuery.filename === query.filename) {
                queryItem.classList.add('selected-query');
                queryItem.style.background = '#e0eaff'; // blu chiaro
                queryItem.style.borderLeft = '4px solid #2563eb'; // blu più scuro
            } else {
                queryItem.style.background = '';
                queryItem.style.borderLeft = '';
            }
            queryItem.onclick = (e) => {
                document.querySelectorAll('.query-item').forEach(item => {
                    item.classList.remove('selected-query');
                    item.style.background = '';
                    item.style.borderLeft = '';
                });
                queryItem.classList.add('selected-query');
                queryItem.style.background = '#e0eaff';
                queryItem.style.borderLeft = '4px solid #2563eb';
                this.selectQuery(query.filename, e);
            };
            // Mostra solo gruppo+nome
            queryItem.innerHTML = `
                <div class="text-sm font-medium text-gray-900">${this._getQueryDisplayName(query.filename)}</div>
                <div class="text-xs text-gray-500 mt-1">${query.description || 'Nessuna descrizione'}</div>
                <div class="text-xs text-gray-400 mt-1">
                    <i class="fas fa-cog mr-1"></i>${query.parameters.length} parametri
                </div>
            `;
            queryList.appendChild(queryItem);
        });
    }

    _getQueryDisplayName(filename) {
        // BOSC-NXV-001--Accessi operatori.sql -> NXV-001--Accessi operatori
        const firstDash = filename.indexOf('-');
        if (firstDash === -1) return filename;
        let rest = filename.substring(firstDash + 1);
        // Rimuovi estensione
        if (rest.endsWith('.sql')) rest = rest.slice(0, -4);
        return rest;
    }
    
    async selectQuery(filename) {
        try {
            // Carica dettagli query
            const response = await fetch(`/api/queries/${filename}`);
            const query = await response.json();
            if (!response.ok) {
                throw new Error(query.detail || 'Errore nel caricamento della query');
            }
            this.currentQuery = query;
            this.renderQueryList(); // Aggiorna evidenza
            this.renderParametersForm(query);
            // Rimuovi risultati precedenti
            this.lastResults = null;
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) resultsSection.classList.add('hidden');
            // Aggiorna barra blu: reset righe e tempo
            const statusBar = document.getElementById('statusConnection');
            if (statusBar) {
                statusBar.innerHTML = `Connessione: <b>${this.currentConnection || 'Nessuna'}</b> Query: <b>${query.title || query.filename}</b>`;
            }
            this.updateStatusBar();
        } catch (error) {
            console.error('Errore nella selezione della query:', error);
            this.showError('Errore nella selezione della query: ' + error.message);
        }
    }
    
    renderParametersForm(query) {
        const parametersSection = document.getElementById('parametersSection');
        const noQuerySelected = document.getElementById('noQuerySelected');
        const parametersForm = document.getElementById('parametersForm');
        
        if (query.parameters.length === 0) {
            parametersForm.innerHTML = '<p class="text-gray-500 text-sm">Questa query non richiede parametri.</p>';
        } else {
            parametersForm.innerHTML = '';
            
            query.parameters.forEach(param => {
                const paramDiv = document.createElement('div');
                paramDiv.className = 'parameter-group';
                
                const isRequired = param.required;
                const inputClass = isRequired ? 'parameter-required' : 'parameter-optional';
                
                paramDiv.innerHTML = `
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                        ${param.name}
                        ${isRequired ? '<span class="text-red-500">*</span>' : '<span class="text-gray-400">(opzionale)</span>'}
                    </label>
                    <input 
                        type="text" 
                        id="param_${param.name}" 
                        name="${param.name}"
                        value="${param.default_value || ''}"
                        placeholder="${this.getParameterPlaceholder(param)}"
                        class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${inputClass}"
                    />
                    ${param.description ? `<p class="text-xs text-gray-500 mt-1">${param.description}</p>` : ''}
                `;
                
                parametersForm.appendChild(paramDiv);
            });
        }
        
        parametersSection.classList.remove('hidden');
        noQuerySelected.classList.add('hidden');
    }
    
    getParameterPlaceholder(param) {
        switch (param.parameter_type) {
            case 'date':
                return 'dd/mm/yyyy';
            case 'datetime':
                return 'dd/mm/yyyy HH:mm:ss';
            case 'integer':
                return 'Numero intero';
            case 'float':
                return 'Numero decimale';
            case 'boolean':
                return 'true/false';
            default:
                return 'Inserisci valore';
        }
    }
    
    async executeQuery() {
        if (!this.currentQuery || !this.currentConnection) {
            this.showError('Seleziona una connessione e una query prima di procedere');
            return;
        }
        
        try {
            this.showLoading(true);
            
            // Raccoglie parametri dal form
            const parameters = {};
            const form = document.getElementById('parametersForm');
            const inputs = form.querySelectorAll('input[name]');
            
            inputs.forEach(input => {
                if (input.value.trim()) {
                    parameters[input.name] = input.value.trim();
                }
            });
            
            // Esegue la query
            const response = await fetch('/api/queries/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query_filename: this.currentQuery.filename,
                    connection_name: this.currentConnection,
                    parameters: parameters,
                    limit: 1000
                })
            });
            
            const result = await response.json();
            
            if (!response.ok || !result.success) {
                throw new Error(result.error_message || result.detail || 'Errore nell\'esecuzione della query');
            }
            
            this.lastResults = result;
            this.renderResults(result);
            this.updateStatusBar();
            
        } catch (error) {
            console.error('Errore nell\'esecuzione della query:', error);
            this.showError('Errore nell\'esecuzione della query: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    renderResults(result) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsTable = document.getElementById('resultsTable');
        const errorSection = document.getElementById('errorSection');
        // Nascondi errori precedenti
        errorSection.classList.add('hidden');
        if (result.data.length === 0) {
            resultsTable.innerHTML = `
                <thead></thead>
                <tbody>
                    <tr>
                        <td class="px-6 py-4 text-center text-gray-500 text-sm">
                            <i class="fas fa-inbox text-3xl mb-2"></i><br>
                            Nessun risultato trovato
                        </td>
                    </tr>
                </tbody>
            `;
        } else {
            // Genera header blu
            const thead = resultsTable.querySelector('thead');
            thead.innerHTML = `
                <tr class="bg-blue-600 text-white">
                    ${result.column_names.map(col => `<th class="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider">${col}</th>`).join('')}
                </tr>
            `;
            // Genera filtri
            this.renderFilters(result.column_names);
            // Genera righe
            this.renderTableRows(result.data);
        }
        resultsSection.classList.remove('hidden');
    }
    
    renderFilters(columnNames) {
        const filtersRow = document.getElementById('filtersRow');
        filtersRow.innerHTML = '';
        
        columnNames.forEach(col => {
            const filterDiv = document.createElement('div');
            filterDiv.innerHTML = `
                <input 
                    type="text" 
                    placeholder="Filtra ${col}..."
                    class="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    onkeyup="psittTool.filterTable('${col}', this.value)"
                />
            `;
            filtersRow.appendChild(filterDiv);
        });
        
        filtersRow.classList.remove('hidden');
    }
    
    renderTableRows(data) {
        const tbody = document.getElementById('resultsTable').querySelector('tbody');
        tbody.innerHTML = '';
        data.forEach((row, idx) => {
            const tr = document.createElement('tr');
            // Colori alterni con maggiore contrasto
            tr.className = idx % 2 === 0 ? 'bg-white hover:bg-blue-100' : 'bg-blue-50 hover:bg-blue-200';
            Object.values(row).forEach(value => {
                const td = document.createElement('td');
                td.className = 'px-6 py-4 text-sm text-gray-900';
                td.textContent = value !== null ? value : '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }
    
    filterTable(column, value) {
        this.filters[column] = value.toLowerCase();
        this.applyFiltersAndSorting();
    }
    
    sortTable(column) {
        // Toggle sorting direction
        if (this.sorting.column === column) {
            this.sorting.direction = this.sorting.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.sorting.column = column;
            this.sorting.direction = 'asc';
        }
        
        this.applyFiltersAndSorting();
    }
    
    applyFiltersAndSorting() {
        if (!this.lastResults) return;
        
        let filteredData = [...this.lastResults.data];
        
        // Applica filtri
        Object.keys(this.filters).forEach(column => {
            const filterValue = this.filters[column];
            if (filterValue) {
                filteredData = filteredData.filter(row => {
                    const cellValue = row[column];
                    return cellValue && cellValue.toString().toLowerCase().includes(filterValue);
                });
            }
        });
        
        // Applica ordinamento
        if (this.sorting.column) {
            filteredData.sort((a, b) => {
                const aValue = a[this.sorting.column];
                const bValue = b[this.sorting.column];
                
                if (aValue < bValue) return this.sorting.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return this.sorting.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        
        this.renderTableRows(filteredData);
        this.updateStatusBar(filteredData.length);
    }
    
    async switchConnection(connectionName) {
        try {
            const response = await fetch('/api/connections/switch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    connection_name: connectionName
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Errore nel cambio connessione');
            }
            
            this.currentConnection = connectionName;
            // Non assumere che sia connessa, testa prima
            this.updateConnectionStatus('testing', connectionName);
            
            // Testa la connessione in background
            setTimeout(() => {
                this.testCurrentConnection(connectionName);
            }, 300);
            
            // Aggiorna la lista delle query filtrate
            this.renderQueryList();
            
            // Reset query corrente se non più compatibile
            const filteredQueries = this.filterQueriesByConnection();
            if (this.currentQuery && !filteredQueries.some(q => q.filename === this.currentQuery.filename)) {
                this.currentQuery = null;
                document.getElementById('parametersSection').classList.add('hidden');
                document.getElementById('noQuerySelected').classList.remove('hidden');
            }
            
        } catch (error) {
            console.error('Errore nel cambio connessione:', error);
            this.showError('Errore nel cambio connessione: ' + error.message);
        }
    }
    
    async testConnection() {
        const connectionName = document.getElementById('connectionSelector').value;
        
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/connections/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    connection_name: connectionName
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Errore nel test della connessione');
            }
            
            if (result.success) {
                this.updateConnectionStatus('connected', connectionName);
                this.showSuccess(`Connessione testata con successo (${result.response_time_ms}ms)`);
            } else {
                this.updateConnectionStatus('error', connectionName);
                
                // Costruisci messaggio errore dettagliato
                let errorDetails = result.error_message || 'Test connessione fallito';
                
                // Aggiungi codice errore se disponibile
                if (result.error_code) {
                    errorDetails = `[${result.error_code}] ${errorDetails}`;
                }
                
                // Mostra errore dettagliato con codice e descrizione
                this.showError(`Test connessione fallito: ${errorDetails}`, {
                    title: 'Errore Connessione Database',
                    details: {
                        'Connessione': connectionName,
                        'Tempo risposta': `${result.response_time_ms}ms`,
                        'Errore': errorDetails
                    }
                });
                
                throw new Error(errorDetails);
            }
            
        } catch (error) {
            console.error('Errore nel test connessione:', error);
            this.updateConnectionStatus('error', connectionName);
            this.showError('Test connessione fallito: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadConnectionStatus() {
        try {
            const response = await fetch('/api/connections/current');
            const data = await response.json();
            
            if (response.ok) {
                this.currentConnection = data.current_connection;
                // NON assumere che sia connesso, testa effettivamente
                this.updateConnectionStatus('testing', data.current_connection);
                // Testa la connessione in background
                setTimeout(() => {
                    this.testCurrentConnection(data.current_connection);
                }, 500);
            }
        } catch (error) {
            console.error('Errore nel caricamento stato connessione:', error);
            this.updateConnectionStatus('error', 'Errore caricamento');
        }
    }
    
    async testCurrentConnection(connectionName) {
        try {
            const response = await fetch('/api/connections/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    connection_name: connectionName
                })
            });
            const result = await response.json();
            
            if (result.success) {
                this.updateConnectionStatus('connected', connectionName);
                console.info(`Connessione ${connectionName} stabilita con successo (${result.response_time_ms}ms)`);
            } else {
                this.updateConnectionStatus('error', connectionName);
                const code = result.error_code || 'N/A';
                const msg = result.error_message || 'Errore sconosciuto';
                console.error(`Test connessione ${connectionName} fallito: [${code}] ${msg}`);
            }
        } catch (error) {
            console.error('Errore nel test connessione:', error);
            this.updateConnectionStatus('error', connectionName);
        }
    }
    
    updateConnectionStatus(status, connectionName) {
        const statusElement = document.getElementById('connectionStatus');
        const statusBar = document.getElementById('statusConnection');
        let statusClass, statusText, statusIcon;
        switch (status) {
            case 'connected':
                statusClass = 'text-green-600';
                statusText = 'Connesso';
                statusIcon = 'fas fa-check-circle text-green-500';
                // Aggiorna la lista delle query disponibili quando la connessione diventa attiva
                this.renderQueryList();
                break;
            case 'testing':
                statusClass = 'text-yellow-600';
                statusText = 'Test in corso...';
                statusIcon = 'fas fa-spinner fa-spin text-yellow-500';
                break;
            case 'error':
                statusClass = 'text-red-600';
                statusText = 'Errore';
                statusIcon = 'fas fa-exclamation-circle text-red-500';
                break;
            default:
                statusClass = 'text-gray-600';
                statusText = 'Disconnesso';
                statusIcon = 'fas fa-circle text-gray-400';
        }
        if (statusElement) {
            statusElement.className = `ml-2 font-semibold ${statusClass}`;
            statusElement.innerHTML = `<i class="${statusIcon}"></i> ${statusText}`;
        }
        if (statusBar) {
            statusBar.innerHTML = `Connessione: <b>${connectionName || 'Nessuna'}</b>`;
        }
    }
    
    updateStatusBar(filteredCount = null) {
        const statusQuery = document.getElementById('statusQuery');
        const statusQueryName = document.getElementById('statusQueryName');
        const statusRecords = document.getElementById('statusRecords');
        const recordCount = document.getElementById('recordCount');
        const statusTime = document.getElementById('statusTime');
        const executionTime = document.getElementById('executionTime');
        
        if (this.currentQuery) {
            statusQuery.classList.remove('hidden');
            statusQueryName.textContent = this.currentQuery.title || this.currentQuery.filename;
        }
        
        if (this.lastResults) {
            statusRecords.classList.remove('hidden');
            statusTime.classList.remove('hidden');
            
            const count = filteredCount !== null ? filteredCount : this.lastResults.row_count;
            const total = this.lastResults.row_count;
            
            recordCount.textContent = filteredCount !== null ? `${count}/${total}` : total.toString();
            executionTime.textContent = `${this.lastResults.execution_time_ms.toFixed(0)}ms`;
        }
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }
    
    showError(message, options = {}) {
        const errorSection = document.getElementById('errorSection');
        const errorMessage = document.getElementById('errorMessage');
        
        // Se ci sono dettagli, costruisci messaggio completo
        if (options.details) {
            let detailsHTML = `<strong>${options.title || 'Errore'}:</strong> ${message}<br><br>`;
            Object.entries(options.details).forEach(([key, value]) => {
                detailsHTML += `<strong>${key}:</strong> ${value}<br>`;
            });
            errorMessage.innerHTML = detailsHTML;
        } else {
            errorMessage.textContent = message;
        }
        
        errorSection.classList.remove('hidden');
        
        // Auto-hide dopo 15 secondi per errori dettagliati
        setTimeout(() => {
            errorSection.classList.add('hidden');
        }, options.details ? 15000 : 10000);
    }
    
    showSuccess(message) {
        // Implementa notifica di successo (toast, etc)
        console.log('Success:', message);
    }
    
    async exportResults(format) {
        if (!this.lastResults || !this.currentQuery) {
            this.showError('Nessun risultato da esportare');
            console.warn('Export fallito: nessun risultato disponibile');
            return;
        }
        try {
            this.showLoading(true);
            const columns = this.lastResults.column_names;
            const data = this.lastResults.data;
            let filenameBase = (this.currentQuery.title || this.currentQuery.filename).replace(/[^a-zA-Z0-9-_]/g, '_');
            console.log(`[EXPORT] Format: ${format}`);
            console.log(`[EXPORT] Columns:`, columns);
            console.log(`[EXPORT] Data:`, data);
            if (format === 'csv') {
                // CSV
                let csv = columns.join(';') + '\n';
                data.forEach(row => {
                    csv += columns.map(col => {
                        let val = row[col];
                        if (val === null || val === undefined) return '';
                        // Escape doppie virgolette
                        val = String(val).replace(/"/g, '""');
                        // Se contiene ; o " o newline, racchiudi tra "
                        if (/;|"|\n/.test(val)) val = '"' + val + '"';
                        return val;
                    }).join(';') + '\n';
                });
                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = filenameBase + '.csv';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else if (format === 'excel') {
                console.log('[EXPORT] Tentativo export Excel...');
                if (typeof XLSX === 'undefined') {
                    this.showError('Libreria SheetJS non caricata.');
                    console.error('[EXPORT] XLSX non definito!');
                    return;
                }
                try {
                    const ws = XLSX.utils.json_to_sheet(data, { header: columns });
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, 'Risultati');
                    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
                    console.log('[EXPORT] Workbook generato:', wb);
                    const blob = new Blob([wbout], { type: 'application/octet-stream' });
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = filenameBase + '.xlsx';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    console.log('[EXPORT] Download Excel avviato');
                } catch (err) {
                    console.error('[EXPORT] Errore generazione Excel:', err);
                    this.showError('Errore generazione Excel: ' + err.message);
                }
            } else {
                this.showError('Formato export non supportato');
                console.warn('[EXPORT] Formato non supportato:', format);
            }
        } catch (error) {
            console.error('Errore nell\'export:', error);
            this.showError('Errore nell\'export: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
}

// Inizializza l'applicazione
let psittTool;
document.addEventListener('DOMContentLoaded', () => {
    psittTool = new PSITTool();
});