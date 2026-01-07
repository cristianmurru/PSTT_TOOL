function showEditForm(item) {
  renderEditForm(item); // funzione già esistente che popola il form
  // assicurare visibilità campi email se sharing = "Email"
  if (typeof applySharingVisibility === 'function') applySharingVisibility();
  requestAnimationFrame(() => focusAndScrollToForm());
}

function showAddForm() {
  renderAddForm(); // funzione già esistente che popola il form
  if (typeof applySharingVisibility === 'function') applySharingVisibility();
  requestAnimationFrame(() => focusAndScrollToForm());
}

function focusAndScrollToForm() {
  const container =
    document.getElementById('scheduleFormContainer') ||
    document.querySelector('#schedule-form, #edit-form, #add-form');
  if (!container) return;

  // Scroll dolce al form
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Focus al primo campo editabile
  const firstField = container.querySelector(
    'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])'
  );
  if (firstField) firstField.focus({ preventScroll: true });

  // Evidenziazione temporanea del blocco per feedback visivo
  container.classList.add('focus-ring');
  setTimeout(() => container.classList.remove('focus-ring'), 1200);
}