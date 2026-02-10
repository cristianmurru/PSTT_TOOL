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
        this.selectedSubdir = 'ALL';
        this.editorFilename = null;
        this.editorMode = 'view'; // 'view' | 'edit'
        
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

        // Return to selection button (in results header)
        const returnBtn = document.getElementById('returnToSelectionBtn');
        if (returnBtn) {
            returnBtn.addEventListener('click', () => {
                this.returnToSelection();
            });
        }

        // Subdirectory selector (se presente in pagina)
        const subdirSelector = document.getElementById('subdirSelector');
        if (subdirSelector) {
            subdirSelector.addEventListener('change', (e) => {
                this.selectedSubdir = e.target.value || 'ALL';
                this.renderQueryList();
            });
        }

        // SQL Editor buttons
        const formatBtn = document.getElementById('formatSqlBtn');
        const suggestBtn = document.getElementById('suggestSqlBtn');
        const saveBtn = document.getElementById('saveSqlBtn');
        const returnEditorBtn = document.getElementById('returnToSelectionEditorBtn');
        if (formatBtn) formatBtn.addEventListener('click', () => this.formatSql());
        if (suggestBtn) suggestBtn.addEventListener('click', () => this.suggestSql());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveSql());
        if (returnEditorBtn) {
            returnEditorBtn.addEventListener('click', () => {
                this.returnToSelection();
                const section = document.getElementById('sqlEditorSection');
                if (section) section.classList.add('hidden');
            });
        }
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
            this.populateSubdirSelector();
            this.renderQueryList();
            
        } catch (error) {
            console.error('Errore nel caricamento delle query:', error);
            this.showError('Errore nel caricamento delle query: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    returnToSelection() {
        // Hide results and reset grid, filters and counters
        try {
            const resultsSection = document.getElementById('resultsSection');
            const filtersRow = document.getElementById('filtersRow');
            const resultsTable = document.getElementById('resultsTable');

            // Reset internal state
            this.lastResults = null;
            this.fullResults = null;
            this.lastResultsIsPreview = false;
            this.filters = {};
            this.sorting = {};

            if (resultsSection) resultsSection.classList.add('hidden');
            if (filtersRow) {
                filtersRow.classList.add('hidden');
                const grid = filtersRow.querySelector('.grid');
                if (grid) grid.innerHTML = '';
                else filtersRow.innerHTML = '';
            }
            if (resultsTable) {
                const thead = resultsTable.querySelector('thead');
                const tbody = resultsTable.querySelector('tbody');
                if (thead) thead.innerHTML = '';
                if (tbody) tbody.innerHTML = '';
            }

            // Hide SQL editor section and suggestions as well
            const editorSection = document.getElementById('sqlEditorSection');
            const suggestions = document.getElementById('sqlSuggestions');
            if (editorSection) editorSection.classList.add('hidden');
            if (suggestions) suggestions.classList.add('hidden');

            // Update status bar: keep query name if selected, but clear counts/time
            this.updateStatusBar();

            // Scroll to selection section and focus for keyboard navigation
            const selection = document.getElementById('selectionSection') || document.body;
            selection.setAttribute('tabindex', '-1');
            selection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            try { selection.focus({ preventScroll: true }); } catch (e) {}

            // Reset editor mode label and hide suggest button to avoid stale state
            try {
                const modeLabel = document.getElementById('sqlEditorModeLabel');
                const suggestBtn = document.getElementById('suggestSqlBtn');
                if (modeLabel) modeLabel.textContent = '';
                if (suggestBtn) suggestBtn.classList.add('hidden');
            } catch (e) { /* ignore */ }
        } catch (e) {
            console.warn('Errore nel ritorno alla selezione:', e);
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
        let filteredQueries = this.filterQueriesByConnection();
        // Escludi alcune sottocartelle dalla Home: tmp e schedulazioni
        filteredQueries = filteredQueries.filter(q => {
            const sd = (q.subdirectory || '').toLowerCase();
            return sd !== 'tmp' && sd !== '_tmp' && sd !== 'schedulazioni';
        });
        // Filtra per sottodirectory se selezionata
        if (this.selectedSubdir && this.selectedSubdir !== 'ALL') {
            filteredQueries = filteredQueries.filter(q => {
                const sd = (q.subdirectory || '').replace(/\\/g, '/');
                return sd === this.selectedSubdir;
            });
        }
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
            queryItem.setAttribute('data-filename', query.filename);
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
                    ${query.subdirectory ? `<span class=\"ml-2\"><i class=\"fas fa-folder-open mr-1\"></i>${query.subdirectory}</span>` : ''}
                </div>
            `;
            queryList.appendChild(queryItem);
        });
    }

    resolveFilenameFromItem(item) {
        if (!item) return null;
        return item.getAttribute('data-filename');
    }

    populateSubdirSelector() {
        const selector = document.getElementById('subdirSelector');
        if (!selector) return;
        // Costruisci l'elenco delle sottocartelle presenti, escludendo tmp e schedulazioni
        const set = new Set();
        (this.queries || []).forEach(q => {
            const sd = (q.subdirectory || '').replace(/\\/g, '/');
            if (sd && sd.toLowerCase() !== 'tmp' && sd.toLowerCase() !== '_tmp' && sd.toLowerCase() !== 'schedulazioni') {
                set.add(sd);
            }
        });
        const subdirs = Array.from(set).sort();
        selector.innerHTML = '';
        const optAll = document.createElement('option');
        optAll.value = 'ALL';
        optAll.textContent = 'Tutte le cartelle';
        selector.appendChild(optAll);
        subdirs.forEach(sd => {
            const opt = document.createElement('option');
            opt.value = sd;
            opt.textContent = sd;
            selector.appendChild(opt);
        });
        // Mantieni selezione corrente se valida, altrimenti resetta ad ALL
        const currentValid = this.selectedSubdir === 'ALL' || subdirs.includes(this.selectedSubdir);
        selector.value = currentValid ? this.selectedSubdir : 'ALL';
        this.selectedSubdir = selector.value;
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
            // Rimuovi risultati precedenti e reset stato export/preview
            this.lastResults = null;
            this.fullResults = null;
            this.lastResultsIsPreview = false;
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) resultsSection.classList.add('hidden');
            // Aggiorna barra blu: reset righe e tempo
            const statusBar = document.getElementById('statusConnection');
            if (statusBar) {
                // Mostra solo la connessione; il nome query viene gestito da #statusQuery
                statusBar.innerHTML = `Connessione: <b>${this.currentConnection || 'Nessuna'}</b>`;
            }
            this.updateStatusBar();
        } catch (error) {
            console.error('Errore nella selezione della query:', error);
            this.showError('Errore nella selezione della query: ' + error.message);
        }
    }

    async openSqlViewer(filename) {
        try {
            const resp = await fetch(`/api/queries/${filename}`);
            const info = await resp.json();
            if (!resp.ok) throw new Error(info.detail || 'Errore caricamento contenuto');
            const section = document.getElementById('sqlEditorSection');
            const editor = document.getElementById('sqlEditor');
            const saveBtn = document.getElementById('saveSqlBtn');
            const suggestBtn = document.getElementById('suggestSqlBtn');
            const modeLabel = document.getElementById('sqlEditorModeLabel');
            const sugg = document.getElementById('sqlSuggestions');
            if (!section || !editor) return;
            this.editorFilename = filename;
            this.editorMode = 'view';
            editor.value = info.sql_content || '';
            editor.setAttribute('readonly', 'readonly');
            if (saveBtn) saveBtn.classList.add('loading');
            if (suggestBtn) {
                // Force-disable in view mode and hide to avoid CSS conflicts
                try {
                    suggestBtn.classList.add('hidden');
                    suggestBtn.classList.add('opacity-50');
                    suggestBtn.classList.add('pointer-events-none');
                    suggestBtn.setAttribute('disabled', 'disabled');
                    suggestBtn.style.display = 'none';
                } catch (e) { /* ignore */ }
            }
            // Hide any previous editor notice
            try {
                const notice = document.getElementById('editorNotice');
                if (notice) notice.classList.add('hidden');
            } catch (e) { /* ignore */ }
            if (modeLabel) modeLabel.textContent = '(Visualizzazione)';
            section.classList.remove('hidden');
            if (sugg) sugg.classList.add('hidden');
            // Focus editor area below status bar
            try {
                section.setAttribute('tabindex', '0');
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                editor.setAttribute('tabindex', '0');
                editor.focus({ preventScroll: true });
            } catch (e) { /* ignore */ }
        } catch (e) {
            console.error('Visualizza SQL fallita:', e);
            this.showError('Errore apertura Visualizza SQL: ' + e.message);
        }
    }

    async openSqlEditor(filename) {
        try {
            const resp = await fetch(`/api/queries/${filename}`);
            const info = await resp.json();
            if (!resp.ok) throw new Error(info.detail || 'Errore caricamento contenuto');
            const section = document.getElementById('sqlEditorSection');
            const editor = document.getElementById('sqlEditor');
            const saveBtn = document.getElementById('saveSqlBtn');
            const suggestBtn = document.getElementById('suggestSqlBtn');
            const modeLabel = document.getElementById('sqlEditorModeLabel');
            const sugg = document.getElementById('sqlSuggestions');
            if (!section || !editor) return;
            // Block editing in production env (UI safeguard)
            try {
                const env = document.body.getAttribute('data-app-env') || '';
                if (env && env.toLowerCase().includes('produzione')) {
                    this.showError('Modifica disabilitata in ambiente di Produzione');
                    return;
                }
            } catch (e) { /* ignore */ }
            this.editorFilename = filename;
            this.editorMode = 'edit';
            editor.value = info.sql_content || '';
            editor.removeAttribute('readonly');
            if (saveBtn) saveBtn.classList.remove('loading');
            if (suggestBtn) {
                // Enable and show in edit mode
                try {
                    suggestBtn.classList.remove('hidden');
                    suggestBtn.classList.remove('opacity-50');
                    suggestBtn.classList.remove('pointer-events-none');
                    suggestBtn.removeAttribute('disabled');
                    suggestBtn.style.display = '';
                } catch (e) { /* ignore */ }
            }
            // Hide any previous editor notice
            try {
                const notice = document.getElementById('editorNotice');
                if (notice) notice.classList.add('hidden');
            } catch (e) { /* ignore */ }
            if (modeLabel) modeLabel.textContent = '(Modifica)';
            section.classList.remove('hidden');
            if (sugg) sugg.classList.add('hidden');
            // Focus editor area below status bar
            try {
                section.setAttribute('tabindex', '0');
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                editor.setAttribute('tabindex', '0');
                editor.focus({ preventScroll: true });
            } catch (e) { /* ignore */ }
        } catch (e) {
            console.error('Modifica SQL fallita:', e);
            this.showError('Errore apertura Modifica SQL: ' + e.message);
        }
    }

    async formatSql() {
        try {
            const editor = document.getElementById('sqlEditor');
            if (!editor || !this.editorFilename) return;
            const sql = editor.value || '';
            const resp = await fetch(`/api/queries/${this.editorFilename}/format`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql_content: sql })
            });
            if (resp.ok) {
                const data = await resp.json();
                editor.value = (data && data.formatted) ? data.formatted : sql;
            } else {
                // Fallback client-side formatter when endpoint not available
                editor.value = this.basicFormatSql(sql);
                this.showSuccess('Formattazione locale applicata');
            }
        } catch (e) {
            console.error('Format SQL fallita:', e);
            this.showError('Errore formattazione SQL: ' + e.message);
        }
    }

    basicFormatSql(sql) {
        try {
            const keywords = [
                'select', 'from', 'where', 'group by', 'order by', 'join', 'left join', 'right join',
                'inner join', 'outer join', 'union', 'with', 'having', 'limit', 'offset', 'insert',
                'update', 'delete'
            ];
            const upkw = (line) => {
                const l = (line || '').trim();
                const low = l.toLowerCase();
                for (const kw of keywords) {
                    if (low.startsWith(kw)) {
                        return kw.toUpperCase() + l.slice(kw.length);
                    }
                }
                return l;
            };
            let s = (sql || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
            let lines = s.split('\n').map(upkw);
            let joined = lines.join('\n');
            [' FROM ', ' WHERE ', ' GROUP BY ', ' ORDER BY ', ' HAVING ', ' JOIN ', ' UNION '].forEach(kw => {
                const re = new RegExp(kw, 'ig');
                joined = joined.replace(re, '\n' + kw.trim() + ' ');
            });
            const outLines = [];
            let indent = false;
            joined.split('\n').forEach(ln => {
                const low = (ln || '').trim().toLowerCase();
                if (low.startsWith('select')) {
                    indent = true;
                    outLines.push(ln);
                    return;
                }
                if (low.startsWith('from')) indent = false;
                if (indent && ln.trim()) outLines.push('  ' + ln);
                else outLines.push(ln);
            });
            // Strip trailing Oracle terminators
            let out = outLines.join('\n').trimEnd();
            while (out.endsWith(';') || out.endsWith('/')) {
                out = out.slice(0, -1).trimEnd();
            }
            return out;
        } catch (e) {
            console.warn('basicFormatSql error:', e);
            return sql;
        }
    }

    async suggestSql() {
        try {
            const editor = document.getElementById('sqlEditor');
            const sugg = document.getElementById('sqlSuggestions');
            const list = document.getElementById('sqlSuggestionsList');
            if (!editor || !this.editorFilename) return;
            const sql = editor.value || '';
            const resp = await fetch(`/api/queries/${this.editorFilename}/suggest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql_content: sql, connection_name: this.currentConnection || '' })
            });
            let data;
            try {
                data = await resp.json();
            } catch (e) {
                throw new Error('Errore parsing risposta suggerimenti');
            }
            if (!resp.ok) throw new Error(data.detail || 'Errore suggerimenti');
            const suggestions = data.suggestions || [];
            const issues = data.issues || [];
            if (list) {
                list.innerHTML = '';
                // Render issues first (errors/warnings)
                issues.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = `${item.type === 'error' ? '[Errore]' : '[Avviso]'} ${item.message}`;
                    li.style.color = item.type === 'error' ? '#b91c1c' : '#92400e';
                    list.appendChild(li);
                });
                // Then suggestions
                suggestions.forEach(s => {
                    const li = document.createElement('li');
                    li.textContent = s;
                    list.appendChild(li);
                });
            }
            if (sugg) sugg.classList.remove('hidden');
        } catch (e) {
            console.error('Suggerimenti SQL falliti:', e);
            this.showError('Errore suggerimenti SQL: ' + e.message);
        }
    }

    async saveSql() {
        try {
            if (this.editorMode !== 'edit' || !this.editorFilename) {
                this.showError('Apri una query in modalità Modifica per salvare');
                return;
            }
            const editor = document.getElementById('sqlEditor');
            const saveBtn = document.getElementById('saveSqlBtn');
            if (!editor) return;
            const sql = editor.value || '';
            // Disable save while processing
            try { if (saveBtn) saveBtn.classList.add('loading'); } catch (e) {}
            const resp = await fetch(`/api/queries/${this.editorFilename}/update`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql_content: sql })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Errore salvataggio');
            // Show inline notice with timestamp and filename
            try {
                const notice = document.getElementById('editorNotice');
                const textEl = document.getElementById('editorNoticeText');
                if (notice && textEl) {
                    const now = new Date();
                    const hh = String(now.getHours()).padStart(2, '0');
                    const mm = String(now.getMinutes()).padStart(2, '0');
                    const ss = String(now.getSeconds()).padStart(2, '0');
                    textEl.textContent = `Query salvata (${this.editorFilename}) alle ${hh}:${mm}:${ss}`;
                    notice.classList.remove('hidden');
                    setTimeout(() => { try { notice.classList.add('hidden'); } catch (e) {} }, 6000);
                }
            } catch (e) { /* ignore */ }
            // Optional global success
            this.showSuccess('Query salvata con successo');
        } catch (e) {
            console.error('Salvataggio SQL fallito:', e);
            this.showError('Errore salvataggio SQL: ' + e.message);
        } finally {
            const saveBtn = document.getElementById('saveSqlBtn');
            try { if (saveBtn) saveBtn.classList.remove('loading'); } catch (e) {}
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
                
                // Detect se è un parametro lista (barcode, codes, ids, list)
                const isListParam = param.name && /list|barcodes?|codes?|ids?/i.test(param.name);
                
                if (isListParam) {
                    // Usa textarea per liste con contatore
                    paramDiv.innerHTML = `
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            ${param.name}
                            ${isRequired ? '<span class="text-red-500">*</span>' : '<span class="text-gray-400">(opzionale)</span>'}
                        </label>
                        <textarea 
                            id="param_${param.name}" 
                            name="${param.name}"
                            rows="5"
                            placeholder="Inserisci valori separati da virgola, newline o già formattati con apici (max 1000)"
                            class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${inputClass} font-mono text-sm"
                        >${param.default_value || ''}</textarea>
                        <div class="flex justify-between items-center mt-1">
                            <p class="text-xs text-gray-500">${param.description || 'Formati supportati: 123,456,789 oppure \'123\',\'456\',\'789\' oppure newline'}</p>
                            <span id="counter_${param.name}" class="text-xs font-medium text-gray-600">0 / 1000</span>
                        </div>
                    `;
                } else {
                    // Input normale per altri parametri
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
                }
                
                parametersForm.appendChild(paramDiv);

                const inputEl = paramDiv.querySelector(`#param_${param.name}`);
                if (!inputEl) return;
                
                if (isListParam) {
                    // Validazione e contatore per liste
                    const counterEl = paramDiv.querySelector(`#counter_${param.name}`);
                    const validate = () => {
                        const val = (inputEl.value || '').trim();
                        if (!val) {
                            if (counterEl) counterEl.textContent = '0 / 1000';
                            if (isRequired) inputEl.classList.add('parameter-invalid');
                            else inputEl.classList.remove('parameter-invalid');
                            return;
                        }
                        
                        // Conta elementi: split per virgola, newline, spazi
                        const items = val.replace(/['"]/g, '').split(/[,\n\r\s]+/).filter(item => item.trim());
                        const count = items.length;
                        
                        if (counterEl) {
                            counterEl.textContent = `${count} / 1000`;
                            if (count > 1000) {
                                counterEl.classList.add('text-red-600', 'font-bold');
                                counterEl.classList.remove('text-gray-600');
                            } else {
                                counterEl.classList.remove('text-red-600', 'font-bold');
                                counterEl.classList.add('text-gray-600');
                            }
                        }
                        
                        if (count > 1000) {
                            inputEl.classList.add('parameter-invalid');
                        } else {
                            inputEl.classList.remove('parameter-invalid');
                        }
                    };
                    
                    inputEl.addEventListener('input', validate);
                    inputEl.addEventListener('blur', validate);
                    validate(); // Initial state
                    
                } else {
                    // Validazione standard per parametri non-lista
                    if (isRequired) {
                        const validate = () => {
                            const hasVal = (inputEl.value || '').trim().length > 0;
                            if (hasVal) {
                                inputEl.classList.remove('parameter-invalid');
                            } else {
                                inputEl.classList.add('parameter-invalid');
                            }
                        };
                        inputEl.addEventListener('input', validate);
                        inputEl.addEventListener('blur', validate);
                        if ((param.default_value || '').trim()) {
                            inputEl.classList.remove('parameter-invalid');
                        }
                    }
                }
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
            
            // Raccoglie parametri dal form (input + textarea)
            const parameters = {};
            const form = document.getElementById('parametersForm');
            const inputs = form.querySelectorAll('input[name], textarea[name]');
            
            // Validazione prima dell'esecuzione
            let hasValidationError = false;
            inputs.forEach(input => {
                const name = input.name;
                const val = (input.value || '').trim();
                
                // Check se è un parametro lista
                const isListParam = name && /list|barcodes?|codes?|ids?/i.test(name);
                
                if (isListParam && val) {
                    // Conta elementi per validare max 1000
                    const items = val.replace(/['"]/g, '').split(/[,\n\r\s]+/).filter(item => item.trim());
                    if (items.length > 1000) {
                        input.classList.add('parameter-invalid');
                        hasValidationError = true;
                        this.showError(`Parametro ${name}: troppi elementi (${items.length}/1000)`);
                        return;
                    }
                }
                
                // Aggiungi parametro se valorizzato
                if (val) {
                    parameters[name] = val;
                }
            });
            
            if (hasValidationError) {
                this.showLoading(false);
                return;
            }

            // Mark empty required fields as invalid before executing
            try {
                const requiredInputs = form.querySelectorAll('input.parameter-required, textarea.parameter-required');
                requiredInputs.forEach(inp => {
                    const v = (inp.value || '').trim();
                    if (!v) {
                        inp.classList.add('parameter-invalid');
                    } else {
                        inp.classList.remove('parameter-invalid');
                    }
                });
            } catch (e) { /* ignore */ }
            
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
                    // UI preview should be limited to 1000 rows to keep responsiveness
                    limit: 1000
                })
            });
            let result;
            try {
                result = await response.json();
            } catch (parseErr) {
                // Fallback: show status code/text for non-JSON responses
                const msg = `HTTP ${response.status} - risposta non valida`;
                throw new Error(msg);
            }
            if (!response.ok || !result.success) {
                const detailMsg = result && (result.error_message || result.detail);
                throw new Error(detailMsg || 'Errore nell\'esecuzione della query');
            }
            
            // Success: ensure required inputs are not shown as invalid anymore
            try {
                const requiredInputs = form.querySelectorAll('input.parameter-required');
                requiredInputs.forEach(inp => inp.classList.remove('parameter-invalid'));
            } catch (e) { /* ignore */ }

            this.lastResults = result;
            // mark as preview only if the returned row_count equals the preview limit
            const previewLimit = 1000;
            this.lastResultsIsPreview = (result.row_count === previewLimit);
            // If the result contains less than the preview limit, treat it as full dataset and cache it
            if (result.row_count < previewLimit) {
                this.fullResults = result;
                this.lastResultsIsPreview = false;
            } else {
                // clear any cached fullResults for previous queries
                this.fullResults = null;
            }
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

        // Focus results and scroll into view after execution
        try {
            const resultsContainer = document.querySelector('.table-container');
            const table = document.getElementById('resultsTable');
            if (resultsContainer) {
                resultsContainer.setAttribute('tabindex', '0');
                resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                resultsContainer.focus({ preventScroll: true });
            } else if (table) {
                table.setAttribute('tabindex', '0');
                table.scrollIntoView({ behavior: 'smooth', block: 'start' });
                table.focus({ preventScroll: true });
            }
        } catch (e) { /* ignore */ }
    }
    
    renderFilters(columnNames) {
        const filtersRow = document.getElementById('filtersRow');
        const gridContainer = filtersRow ? filtersRow.querySelector('.grid') : null;
        const target = gridContainer || filtersRow;
        if (!target) return;
        target.innerHTML = '';
        // Mostra filtri solo per i primi 6 campi del recordset per evitare UI affollata
        const VISIBLE_FILTERS = 6;
        const colsToFilter = Array.isArray(columnNames) ? columnNames.slice(0, VISIBLE_FILTERS) : [];
        
        colsToFilter.forEach(col => {
            const filterDiv = document.createElement('div');
            filterDiv.innerHTML = `
                <input 
                    type="text" 
                    placeholder="Filtra ${col}..."
                    class="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    onkeyup="psittTool.filterTable('${col}', this.value)"
                />
            `;
            target.appendChild(filterDiv);
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
    
    async filterTable(column, value) {
        this.filters[column] = value.toLowerCase();
        // Ensure we have the full dataset before applying filters so filters work on entire result set
        try {
            await this.ensureFullDataset();
        } catch (err) {
            console.warn('Impossibile recuperare dataset completo per filtri:', err);
        }
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

        // Usa il dataset completo se disponibile, altrimenti la preview
        const source = this.fullResults ? this.fullResults : this.lastResults;
        let filteredData = Array.isArray(source.data) ? [...source.data] : [];
        
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

            // Ripulisci stato risultati/preview come quando si seleziona una nuova query
            this.lastResults = null;
            this.fullResults = null;
            this.lastResultsIsPreview = false;
            this.filters = {};
            this.sorting = {};
            // Ripulisci anche la query selezionata e UI del form
            this.currentQuery = null;
            const parametersSection = document.getElementById('parametersSection');
            const noQuerySelected = document.getElementById('noQuerySelected');
            if (parametersSection) parametersSection.classList.add('hidden');
            if (noQuerySelected) noQuerySelected.classList.remove('hidden');
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) resultsSection.classList.add('hidden');
            this.updateStatusBar();
            
            // Testa la connessione in background
            setTimeout(() => {
                this.testCurrentConnection(connectionName);
            }, 300);
            
            // Aggiorna la lista delle query filtrate
            this.renderQueryList();
            
            // La query viene azzerata indipendentemente dalla compatibilità
            
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
        } else {
            // Hide and clear query name when no query is selected
            try { statusQuery.classList.add('hidden'); } catch (e) {}
            try { statusQueryName.textContent = ''; } catch (e) {}
        }
        
        if (this.lastResults) {
            statusRecords.classList.remove('hidden');
            statusTime.classList.remove('hidden');
            
            // If we have fullResults cached, use its row_count as total
            const total = (this.fullResults && this.fullResults.row_count) ? this.fullResults.row_count : this.lastResults.row_count;
            const count = filteredCount !== null ? filteredCount : this.lastResults.row_count;
            
            recordCount.textContent = filteredCount !== null ? `${count}/${total}` : total.toString();
            const ms = this.lastResults.execution_time_ms || 0;
            const secs = ms / 1000;
            executionTime.textContent = `${ms.toFixed(0)}ms (${secs.toFixed(3)}s)`;
            
            // Show preview notice only when last result is flagged as preview and there is no fullResults cached
            const previewElId = 'previewNotice';
            let previewEl = document.getElementById(previewElId);
            if (this.lastResultsIsPreview && !this.fullResults) {
                if (!previewEl) {
                    previewEl = document.createElement('div');
                    previewEl.id = previewElId;
                    previewEl.className = 'mt-2 px-3 py-2 text-sm text-yellow-800 bg-yellow-100 rounded';
                }
                previewEl.innerHTML = `Preview: visualizzate le prime ${this.lastResults.row_count} righe. I filtri in griglia verranno applicati all'intero dataset dopo il caricamento completo. Premi Export per scaricare il file completo.`;
                if (!document.getElementById(previewElId)) {
                    statusRecords.parentNode.insertBefore(previewEl, statusRecords.nextSibling);
                }
            } else {
                if (previewEl) previewEl.remove();
            }
        }
        else {
            // No last results: clear/hide counters and preview notice
            try {
                statusRecords.classList.add('hidden');
            } catch (e) {}
            try { statusTime.classList.add('hidden'); } catch (e) {}
            try { recordCount.textContent = ''; } catch (e) {}
            try { executionTime.textContent = ''; } catch (e) {}
            const previewEl = document.getElementById('previewNotice');
            if (previewEl) previewEl.remove();
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

    async ensureFullDataset() {
        // If we already cached full results, return them
        if (this.fullResults) return this.fullResults;
        if (!this.currentQuery || !this.lastResults) throw new Error('Nessuna query eseguita');

        this.showLoading(true);
        try {
            const paramsForExport = (this.lastResults && this.lastResults.parameters_used) ? this.lastResults.parameters_used : {};
            const execResponse = await fetch('/api/queries/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_filename: this.currentQuery.filename,
                    connection_name: this.currentConnection,
                    parameters: paramsForExport
                })
            });
            const execResult = await execResponse.json();
            if (!execResponse.ok || !execResult.success) {
                throw new Error(execResult.error_message || execResult.detail || 'Errore recupero dataset completo');
            }
            this.fullResults = execResult;
            // once we have full results, clear preview flag
            this.lastResultsIsPreview = false;
            // re-render UI counts
            this.updateStatusBar();
            return execResult;
        } finally {
            this.showLoading(false);
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
            // Per l'export vogliamo il dataset completo: utilizziamo la cache se presente
            // altrimenti richiediamo al backend i risultati senza limit (backend default None = nessun limite)
            let execResult = this.fullResults;
            if (!execResult) {
                const paramsForExport = (this.lastResults && this.lastResults.parameters_used) ? this.lastResults.parameters_used : {};
                const execResponse = await fetch('/api/queries/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query_filename: this.currentQuery.filename,
                        connection_name: this.currentConnection,
                        parameters: paramsForExport
                    })
                });
                execResult = await execResponse.json();
                if (!execResponse.ok || !execResult.success) {
                    throw new Error(execResult.error_message || execResult.detail || 'Errore nell\'esecuzione export');
                }
                // Cache risultati completi per eventuali successive operazioni (filter/sort/export)
                this.fullResults = execResult;
            }
            // Prefer server-side export to ensure consistency with scheduled exports
            const filenameBase = (this.currentQuery.title || this.currentQuery.filename).replace(/[^a-zA-Z0-9-_]/g, '_');
            console.log(`[EXPORT] Requesting server export: format=${format} rows=${execResult ? execResult.row_count : 'unknown'}`);

            try {
                const exportBody = {
                    query_filename: this.currentQuery.filename,
                    connection_name: this.currentConnection,
                    parameters: (this.lastResults && this.lastResults.parameters_used) ? this.lastResults.parameters_used : {},
                    export_format: format
                };

                const resp = await fetch('/api/queries/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(exportBody)
                });

                if (!resp.ok) {
                    // Try to parse JSON error
                    let errBody = null;
                    try { errBody = await resp.json(); } catch (e) { /* ignore */ }
                    throw new Error((errBody && (errBody.error_message || errBody.detail)) || `Server export failed: ${resp.status}`);
                }

                const blob = await resp.blob();

                // Try to get filename from response headers
                let filename = filenameBase + (format === 'excel' ? '.xlsx' : '.csv');
                const cd = resp.headers.get('content-disposition');
                if (cd) {
                    const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^;"']+)"?/i);
                    if (m && m[1]) {
                        filename = decodeURIComponent(m[1]);
                    }
                }

                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                console.log('[EXPORT] Server download avviato, filename=', filename);
            } catch (err) {
                console.error('[EXPORT] Errore export server:', err);
                this.showError('Errore export server: ' + err.message);
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