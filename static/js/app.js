/**
 * ==============================================================================
 * Touch and Solve Microfinance - Simple JavaScript Helper Script
 * Author: Junior Developer / Learning Project
 * Description: Clean helper functions for sidebar toggling, notifications, 
 *              dialog modals, and client-side loan calculations.
 * ==============================================================================
 */

// Run our scripts once the full HTML document has loaded
document.addEventListener('DOMContentLoaded', () => {

  /* --------------------------------------------------------------------------
     1. SIDEBAR CONTROLLER (Open, Close, Toggle)
     -------------------------------------------------------------------------- */
  
  // Function to open the sidebar
  window.openSidebar = function(e) {
    if (e) { 
      e.preventDefault(); 
      e.stopPropagation(); 
    }
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    
    if (sidebar) sidebar.classList.add('show');
    if (backdrop) backdrop.classList.add('show');
    document.body.style.overflow = 'hidden'; // Stop background page scrolling
  };

  // Function to close the sidebar
  window.closeSidebar = function(e) {
    if (e) { 
      e.preventDefault(); 
      e.stopPropagation(); 
    }
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    
    if (sidebar) sidebar.classList.remove('show');
    if (backdrop) backdrop.classList.remove('show');
    document.body.style.overflow = ''; // Re-enable background scrolling
  };

  // Function to toggle sidebar open or closed
  window.toggleSidebar = function(e) {
    if (e) { 
      e.preventDefault(); 
      e.stopPropagation(); 
    }
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar && sidebar.classList.contains('show')) {
      window.closeSidebar(e);
    } else {
      window.openSidebar(e);
    }
  };

  // Attach click listeners to the toggle and close buttons
  const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
  const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');

  if (sidebarToggleBtn) sidebarToggleBtn.onclick = window.toggleSidebar;
  if (sidebarCloseBtn) sidebarCloseBtn.onclick = window.closeSidebar;
  if (sidebarBackdrop) sidebarBackdrop.onclick = window.closeSidebar;

  // Pressing 'Escape' key on keyboard also closes the sidebar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      window.closeSidebar();
    }
  });



  /* --------------------------------------------------------------------------
     3. POPUP MODAL HANDLERS
     -------------------------------------------------------------------------- */
  // Open modal by element ID
  window.openModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
    }
  };

  // Close modal by element ID
  window.closeModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
    }
  };

  // Close modals when user clicks outside the modal box
  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('active');
      }
    });
  });

  /* --------------------------------------------------------------------------
     4. LOAN ESTIMATE CALCULATOR
     Calculates interest and installments dynamically for both Monthly and Weekly schedules.
     -------------------------------------------------------------------------- */
  const amountInput = document.querySelector('input[name="principal_amount"]');
  const durationInput = document.querySelector('input[name="duration_months"]');
  const frequencySelect = document.querySelector('select[name="installment_frequency"]');
  const productSelect = document.querySelector('select[name="loan_product"]');
  const calcResult = document.getElementById('loan-calc-summary');
  const schemesDataEl = document.getElementById('loan-schemes-data');

  let schemesData = {};
  if (schemesDataEl) {
    try {
      schemesData = JSON.parse(schemesDataEl.textContent.trim());
    } catch (e) {
      console.error('Error parsing schemes data', e);
    }
  }

  function updateLoanCalculation() {
    if (!amountInput || !durationInput || !calcResult) return;
    
    // Read input values
    const amount = parseFloat(amountInput.value) || 0;
    const months = parseInt(durationInput.value) || 0;
    const frequency = frequencySelect ? frequencySelect.value : 'MONTHLY';

    // Determine interest rate from scheme or standard fallback 10%
    let rate = 10.0;
    let schemeName = '';
    if (productSelect && productSelect.value && schemesData[productSelect.value]) {
      const currentScheme = schemesData[productSelect.value];
      rate = parseFloat(currentScheme.rate) || 10.0;
      schemeName = currentScheme.name;
    }

    if (amount > 0 && months > 0) {
      // Formula matches apps/loans/models.py: Interest = Principal * (Rate / 100) * (Months / 12)
      const interest = (amount * (rate / 100.0) * (months / 12.0));
      const totalPayable = amount + interest;

      const isWeekly = (frequency === 'WEEKLY');
      const numInstallments = isWeekly ? (months * 4) : months;
      const installmentAmount = totalPayable / (numInstallments || 1);
      const principalPart = amount / (numInstallments || 1);
      const interestPart = interest / (numInstallments || 1);

      // Show simple summary box with calculated numbers
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
            <strong style="color: #0d6efd;">৳${totalPayable.toFixed(2)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding-top: 6px; border-top: 1px dashed #dee2e6;">
            <span style="color: #6c757d;">
              ${isWeekly ? 'Weekly Installment (' + numInstallments + ' weeks):' : 'Monthly Installment (' + numInstallments + ' months):'}
            </span> 
            <strong style="color: #198754; font-size: 0.95rem;">
              ৳${installmentAmount.toFixed(2)} / ${isWeekly ? 'week' : 'month'}
            </strong>
          </div>
        </div>
      `;
    } else {
      calcResult.innerHTML = '';
    }
  }

  // Scheme select change listener
  if (productSelect) {
    productSelect.addEventListener('change', () => {
      const selectedId = productSelect.value;
      const scheme = schemesData[selectedId];
      if (scheme) {
        if (durationInput && scheme.duration_months) {
          durationInput.value = scheme.duration_months;
        }
        if (frequencySelect && scheme.installment_frequency) {
          frequencySelect.value = scheme.installment_frequency;
        }
        if (amountInput && (!amountInput.value || parseFloat(amountInput.value) === 0)) {
          amountInput.value = scheme.min_amount || '';
        }
      }
      updateLoanCalculation();
    });
  }

  // Recalculate whenever user types in the input boxes or changes frequency
  if (amountInput) amountInput.addEventListener('input', updateLoanCalculation);
  if (durationInput) durationInput.addEventListener('input', updateLoanCalculation);
  if (frequencySelect) frequencySelect.addEventListener('change', updateLoanCalculation);

  // Initial calculation check on page load if inputs have prefilled values
  updateLoanCalculation();

  /* --------------------------------------------------------------------------
     5. MEMBER SEARCH AUTOCOMPLETE
     Enables dynamic search input with keyword suggestions for member selects.
     -------------------------------------------------------------------------- */
  const membersDataEl = document.getElementById('active-members-data');
  let globalMembersList = [];
  if (membersDataEl) {
    try {
      globalMembersList = JSON.parse(membersDataEl.textContent.trim());
    } catch (e) {
      console.error('Error parsing members data', e);
    }
  }

  function initMemberSearch() {
    const searchInputs = document.querySelectorAll('.member-search-input');
    if (!searchInputs || searchInputs.length === 0) return;

    searchInputs.forEach(input => {
      const wrapper = input.closest('.member-search-box-wrapper');
      if (!wrapper) return;

      const targetSelector = input.getAttribute('data-target-select');
      const targetSelect = targetSelector ? document.querySelector(targetSelector) : null;
      const clearBtn = wrapper.querySelector('.member-search-clear');
      const dropdown = wrapper.querySelector('.member-suggestions-dropdown');
      const container = wrapper.closest('.form-group');
      const indicator = container ? container.querySelector('.selected-member-indicator') : null;

      // Use global members list if available, or fallback to select options
      let availableMembers = globalMembersList;
      if (!availableMembers || availableMembers.length === 0) {
        if (targetSelect) {
          availableMembers = Array.from(targetSelect.options)
            .filter(opt => opt.value)
            .map(opt => {
              const parts = opt.text.split(' - ');
              return {
                id: opt.value,
                member_id: parts[0] ? parts[0].trim() : '',
                name: parts.slice(1).join(' - ').trim() || opt.text,
                phone: ''
              };
            });
        }
      }

      let activeIndex = -1;

      function updateIndicator(member) {
        if (!indicator) return;
        if (member) {
          indicator.innerHTML = `<span>✓</span> <div><strong>Selected:</strong> ${member.name} (${member.member_id}) ${member.phone ? '&bull; 📞 ' + member.phone : ''}</div>`;
          indicator.style.display = 'flex';
        } else {
          indicator.innerHTML = '';
          indicator.style.display = 'none';
        }
      }

      function highlightMatch(text, query) {
        if (!text) return '';
        if (!query) return text;
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span style="background: #fef08a; color: #854d0e; font-weight: 700; border-radius: 2px; padding: 0 2px;">$1</span>');
      }

      function renderSuggestions(query) {
        if (!dropdown) return;
        const q = (query || '').trim().toLowerCase();
        activeIndex = -1;

        let matches = availableMembers;
        if (q) {
          matches = availableMembers.filter(m => {
            const nameMatch = m.name && m.name.toLowerCase().includes(q);
            const idMatch = m.member_id && m.member_id.toLowerCase().includes(q);
            const phoneMatch = m.phone && m.phone.toLowerCase().includes(q);
            return nameMatch || idMatch || phoneMatch;
          });
        }

        if (matches.length === 0) {
          dropdown.innerHTML = `
            <div style="padding: 12px; text-align: center; color: #94a3b8; font-size: 0.82rem;">
              No members found matching "<strong>${q}</strong>"
            </div>
          `;
          dropdown.style.display = 'block';
          return;
        }

        dropdown.innerHTML = matches.map((m, index) => `
          <div class="member-suggestion-item" data-id="${m.id}" data-index="${index}" style="padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="member-name-text" style="font-weight: 600; font-size: 0.86rem; color: #1e293b;">
                ${highlightMatch(m.name, q)}
              </div>
              <div class="member-meta-text" style="font-size: 0.74rem; color: #64748b; margin-top: 1px;">
                ${m.phone ? '📞 ' + highlightMatch(m.phone, q) : 'Member'} ${m.email ? '&bull; ' + m.email : ''}
              </div>
            </div>
            <span class="badge badge-primary" style="font-size: 0.72rem; padding: 2px 6px;">
              ${highlightMatch(m.member_id, q)}
            </span>
          </div>
        `).join('');

        dropdown.style.display = 'block';

        // Add mouse interactions
        dropdown.querySelectorAll('.member-suggestion-item').forEach(item => {
          item.addEventListener('mouseenter', () => {
            dropdown.querySelectorAll('.member-suggestion-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
          });
          item.addEventListener('click', () => {
            const memberId = item.getAttribute('data-id');
            const selected = availableMembers.find(m => String(m.id) === String(memberId));
            if (selected) selectMember(selected);
          });
        });
      }

      function selectMember(member) {
        if (targetSelect) {
          targetSelect.value = member.id;
          targetSelect.dispatchEvent(new Event('change'));
        }
        input.value = `${member.member_id} - ${member.name}`;
        if (clearBtn) clearBtn.style.display = 'block';
        updateIndicator(member);
        if (dropdown) dropdown.style.display = 'none';
      }

      function clearSelection() {
        if (targetSelect) {
          targetSelect.value = '';
          targetSelect.dispatchEvent(new Event('change'));
        }
        input.value = '';
        if (clearBtn) clearBtn.style.display = 'none';
        updateIndicator(null);
        renderSuggestions('');
        input.focus();
      }

      // Input typing events
      input.addEventListener('input', () => {
        const val = input.value;
        if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';
        renderSuggestions(val);
      });

      input.addEventListener('focus', () => {
        renderSuggestions(input.value);
      });

      // Keyboard navigation
      input.addEventListener('keydown', (e) => {
        if (!dropdown || dropdown.style.display === 'none') return;
        const items = dropdown.querySelectorAll('.member-suggestion-item');
        if (!items || items.length === 0) return;

        if (e.key === 'ArrowDown') {
          e.preventDefault();
          activeIndex = (activeIndex + 1) % items.length;
          items.forEach((it, idx) => it.classList.toggle('active', idx === activeIndex));
          items[activeIndex].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          activeIndex = (activeIndex - 1 + items.length) % items.length;
          items.forEach((it, idx) => it.classList.toggle('active', idx === activeIndex));
          items[activeIndex].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (activeIndex >= 0 && items[activeIndex]) {
            items[activeIndex].click();
          } else if (items[0]) {
            items[0].click();
          }
        } else if (e.key === 'Escape') {
          dropdown.style.display = 'none';
        }
      });

      if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          clearSelection();
        });
      }

      // Sync if target select is changed directly
      if (targetSelect) {
        targetSelect.addEventListener('change', () => {
          const val = targetSelect.value;
          const found = availableMembers.find(m => String(m.id) === String(val));
          if (found) {
            input.value = `${found.member_id} - ${found.name}`;
            if (clearBtn) clearBtn.style.display = 'block';
            updateIndicator(found);
          } else if (!val) {
            input.value = '';
            if (clearBtn) clearBtn.style.display = 'none';
            updateIndicator(null);
          }
        });

        // Initialize display if targetSelect has initial value
        if (targetSelect.value) {
          const initial = availableMembers.find(m => String(m.id) === String(targetSelect.value));
          if (initial) {
            input.value = `${initial.member_id} - ${initial.name}`;
            if (clearBtn) clearBtn.style.display = 'block';
            updateIndicator(initial);
          }
        }
      }

      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target)) {
          if (dropdown) dropdown.style.display = 'none';
        }
      });
    });
  }

  // Initialize Member Search on page load
  initMemberSearch();
});
