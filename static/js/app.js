/**
 * Touch and Solve Microfinance - Core Application Scripts
 * Features: Sidebar toggle, modal dialogs, dynamic loan calculator,
 * member search autocomplete, and numeric-only input enforcement.
 */
document.addEventListener('DOMContentLoaded', () => {

  /* --------------------------------------------------------------------------
     1. SIDEBAR & MODALS
     -------------------------------------------------------------------------- */
  const sidebar = () => document.getElementById('app-sidebar');
  const backdrop = () => document.getElementById('sidebar-backdrop');

  window.openSidebar = (e) => {
    e?.preventDefault();
    sidebar()?.classList.add('show');
    backdrop()?.classList.add('show');
    document.body.style.overflow = 'hidden';
  };

  window.closeSidebar = (e) => {
    e?.preventDefault();
    sidebar()?.classList.remove('show');
    backdrop()?.classList.remove('show');
    document.body.style.overflow = '';
  };

  window.toggleSidebar = (e) => {
    sidebar()?.classList.contains('show') ? window.closeSidebar(e) : window.openSidebar(e);
  };

  document.getElementById('sidebar-toggle-btn')?.addEventListener('click', window.toggleSidebar);
  document.getElementById('sidebar-close-btn')?.addEventListener('click', window.closeSidebar);
  document.getElementById('sidebar-backdrop')?.addEventListener('click', window.closeSidebar);

  // Modals
  window.openModal = (id) => document.getElementById(id)?.classList.add('active');
  window.closeModal = (id) => document.getElementById(id)?.classList.remove('active');

  // Close modals or sidebar on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.closeSidebar();
      document.querySelectorAll('.modal-backdrop.active').forEach(m => m.classList.remove('active'));
    }
  });

  // Close modals when clicking background backdrop
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
      e.target.classList.remove('active');
    }
  });

  /* --------------------------------------------------------------------------
     2. DYNAMIC LOAN CALCULATOR
     -------------------------------------------------------------------------- */
  const amountInput = document.querySelector('input[name="principal_amount"]');
  const durationInput = document.querySelector('input[name="duration_months"]');
  const frequencySelect = document.querySelector('select[name="installment_frequency"]');
  const productSelect = document.querySelector('select[name="loan_product"]');
  const calcResult = document.getElementById('loan-calc-summary');

  let schemesData = {};
  try {
    const el = document.getElementById('loan-schemes-data');
    if (el) schemesData = JSON.parse(el.textContent.trim());
  } catch (e) {
    console.error('Error parsing schemes data', e);
  }

  function updateLoanCalc() {
    if (!amountInput || !durationInput || !calcResult) return;
    const amount = parseFloat(amountInput.value) || 0;
    const months = parseInt(durationInput.value) || 0;
    const frequency = frequencySelect?.value || 'MONTHLY';
    const scheme = productSelect && schemesData[productSelect.value];
    const rate = scheme ? (parseFloat(scheme.rate) || 10.0) : 10.0;

    if (amount > 0 && months > 0) {
      const interest = amount * (rate / 100.0) * (months / 12.0);
      const total = amount + interest;
      const isWeekly = frequency === 'WEEKLY';
      const installments = isWeekly ? months * 4 : months;
      const perInstallment = total / (installments || 1);

      calcResult.innerHTML = `
        <div style="background: #f8fafc; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px 14px; margin-top: 12px; font-size: 0.85rem;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="color: #6c757d;">Principal Amount:</span>
            <strong>৳${amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="color: #6c757d;">Estimated Interest (${rate}%):</span>
            <strong>৳${interest.toFixed(2)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="color: #6c757d;">Total Repayable:</span>
            <strong style="color: #0d6efd;">৳${total.toFixed(2)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding-top: 6px; border-top: 1px dashed #dee2e6;">
            <span style="color: #6c757d;">${isWeekly ? 'Weekly Installment (' + installments + ' weeks):' : 'Monthly Installment (' + installments + ' months):'}</span>
            <strong style="color: #198754; font-size: 0.95rem;">৳${perInstallment.toFixed(2)} / ${isWeekly ? 'week' : 'month'}</strong>
          </div>
        </div>`;
    } else {
      calcResult.innerHTML = '';
    }
  }

  productSelect?.addEventListener('change', () => {
    const scheme = schemesData[productSelect.value];
    if (scheme) {
      if (durationInput && scheme.duration_months) durationInput.value = scheme.duration_months;
      if (frequencySelect && scheme.installment_frequency) frequencySelect.value = scheme.installment_frequency;
      if (amountInput && (!amountInput.value || parseFloat(amountInput.value) === 0)) {
        amountInput.value = scheme.min_amount || '';
      }
    }
    updateLoanCalc();
  });

  amountInput?.addEventListener('input', updateLoanCalc);
  durationInput?.addEventListener('input', updateLoanCalc);
  frequencySelect?.addEventListener('change', updateLoanCalc);
  updateLoanCalc();

  /* --------------------------------------------------------------------------
     3. MEMBER SEARCH AUTOCOMPLETE
     -------------------------------------------------------------------------- */
  function initMemberSearch() {
    const searchInputs = document.querySelectorAll('.member-search-input');
    if (!searchInputs.length) return;

    let globalMembers = [];
    try {
      const el = document.getElementById('active-members-data');
      if (el) globalMembers = JSON.parse(el.textContent.trim());
    } catch (e) {
      console.error('Error parsing members data', e);
    }

    searchInputs.forEach(input => {
      const wrapper = input.closest('.member-search-box-wrapper');
      if (!wrapper) return;
      const targetSelect = document.querySelector(input.getAttribute('data-target-select') || '');
      const clearBtn = wrapper.querySelector('.member-search-clear');
      const dropdown = wrapper.querySelector('.member-suggestions-dropdown');
      const container = wrapper.closest('.form-group');
      const indicator = container?.querySelector('.selected-member-indicator');

      let members = globalMembers.length ? globalMembers : (targetSelect ? Array.from(targetSelect.options).filter(o => o.value).map(o => {
        const parts = o.text.split(' - ');
        return { id: o.value, member_id: parts[0]?.trim() || '', name: parts.slice(1).join(' - ').trim() || o.text, phone: '' };
      }) : []);

      let activeIndex = -1;

      function setIndicator(m) {
        if (!indicator) return;
        indicator.innerHTML = m ? `<span>✓</span> <div><strong>Selected:</strong> ${m.name} (${m.member_id}) ${m.phone ? '&bull; 📞 ' + m.phone : ''}</div>` : '';
        indicator.style.display = m ? 'flex' : 'none';
      }

      function renderSuggestions(query) {
        if (!dropdown) return;
        const q = (query || '').trim().toLowerCase();
        activeIndex = -1;

        const matches = q ? members.filter(m =>
          (m.name && m.name.toLowerCase().includes(q)) ||
          (m.member_id && m.member_id.toLowerCase().includes(q)) ||
          (m.phone && m.phone.toLowerCase().includes(q))
        ) : members;

        if (!matches.length) {
          dropdown.innerHTML = `<div style="padding: 12px; text-align: center; color: #94a3b8; font-size: 0.82rem;">No members found matching "<strong>${q}</strong>"</div>`;
          dropdown.style.display = 'block';
          return;
        }

        const hl = (txt) => q ? String(txt).replace(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'), '<mark style="background:#fef08a;color:#854d0e;padding:0 2px;border-radius:2px;">$1</mark>') : txt;

        dropdown.innerHTML = matches.map((m, idx) => `
          <div class="member-suggestion-item" data-id="${m.id}" data-index="${idx}" style="padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; font-size: 0.86rem; color: #1e293b;">${hl(m.name || '')}</div>
              <div style="font-size: 0.74rem; color: #64748b;">${m.phone ? '📞 ' + hl(m.phone) : 'Member'} ${m.email ? '&bull; ' + m.email : ''}</div>
            </div>
            <span class="badge badge-primary" style="font-size: 0.72rem; padding: 2px 6px;">${hl(m.member_id || '')}</span>
          </div>
        `).join('');

        dropdown.querySelectorAll('.member-suggestion-item').forEach(item => {
          item.onmouseenter = () => {
            dropdown.querySelectorAll('.member-suggestion-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
          };
          item.onclick = () => {
            const found = members.find(m => String(m.id) === item.dataset.id);
            if (found) selectMember(found);
          };
        });
        dropdown.style.display = 'block';
      }

      function selectMember(m) {
        if (targetSelect) { targetSelect.value = m.id; targetSelect.dispatchEvent(new Event('change')); }
        input.value = `${m.member_id} - ${m.name}`;
        if (clearBtn) clearBtn.style.display = 'block';
        setIndicator(m);
        if (dropdown) dropdown.style.display = 'none';
      }

      function clearMember() {
        if (targetSelect) { targetSelect.value = ''; targetSelect.dispatchEvent(new Event('change')); }
        input.value = '';
        if (clearBtn) clearBtn.style.display = 'none';
        setIndicator(null);
        renderSuggestions('');
        input.focus();
      }

      input.oninput = () => {
        if (clearBtn) clearBtn.style.display = input.value ? 'block' : 'none';
        renderSuggestions(input.value);
      };
      input.onfocus = () => renderSuggestions(input.value);

      input.onkeydown = (e) => {
        if (!dropdown || dropdown.style.display === 'none') return;
        const items = dropdown.querySelectorAll('.member-suggestion-item');
        if (!items.length) return;

        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          activeIndex = e.key === 'ArrowDown' ? (activeIndex + 1) % items.length : (activeIndex - 1 + items.length) % items.length;
          items.forEach((it, idx) => it.classList.toggle('active', idx === activeIndex));
          items[activeIndex]?.scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
          e.preventDefault();
          (items[activeIndex] || items[0])?.click();
        } else if (e.key === 'Escape') {
          dropdown.style.display = 'none';
        }
      };

      if (clearBtn) clearBtn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); clearMember(); };

      if (targetSelect) {
        const syncFromSelect = () => {
          const found = members.find(m => String(m.id) === String(targetSelect.value));
          if (found) {
            input.value = `${found.member_id} - ${found.name}`;
            if (clearBtn) clearBtn.style.display = 'block';
            setIndicator(found);
          } else if (!targetSelect.value) {
            input.value = '';
            if (clearBtn) clearBtn.style.display = 'none';
            setIndicator(null);
          }
        };
        targetSelect.addEventListener('change', syncFromSelect);
        if (targetSelect.value) syncFromSelect();
      }

      document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target) && dropdown) dropdown.style.display = 'none';
      });
    });
  }

  initMemberSearch();

  /* --------------------------------------------------------------------------
     4. NUMERIC-ONLY INPUT RESTRICTION (Phone Numbers & National ID / NID)
     -------------------------------------------------------------------------- */
  function enforceNumericInputs() {
    const allowed = ['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'];
    document.querySelectorAll('input[name*="phone"], input[name*="nid"], input[id*="phone"], input[id*="nid"]').forEach(input => {
      input.setAttribute('inputmode', 'numeric');
      input.setAttribute('pattern', '[0-9]*');

      input.addEventListener('keydown', (e) => {
        if (allowed.includes(e.key) || e.ctrlKey || e.metaKey) return;
        if (!/^[0-9]$/.test(e.key)) e.preventDefault();
      });

      input.addEventListener('input', function() {
        const cleaned = this.value.replace(/\D/g, '');
        if (this.value !== cleaned) this.value = cleaned;
      });

      input.addEventListener('paste', function(e) {
        e.preventDefault();
        const digits = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
        const s = this.selectionStart || 0, end = this.selectionEnd || 0;
        this.value = (this.value || '').substring(0, s) + digits + (this.value || '').substring(end);
        this.selectionStart = this.selectionEnd = s + digits.length;
        this.dispatchEvent(new Event('input', { bubbles: true }));
      });
    });
  }

  enforceNumericInputs();
});
