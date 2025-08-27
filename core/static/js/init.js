document.addEventListener('change', function (e) {
  if (!e.target.classList.contains('rhs-mode')) return;
  const row = e.target.closest('.condition-row');
  const isVar = e.target.value === 'variable';
  row.querySelector('.condition-value').style.display = isVar ? 'none' : '';
  const rhs = row.querySelector('.rhs-input');
  if (rhs) rhs.style.display = isVar ? 'inline-flex' : 'none';
});



form.addEventListener("submit", function () {
  // 1) Clean prior hidden fields so we don't stack them
  // Normalize OTM targets: convert "__custom__" to the number from the sibling input
  document.querySelectorAll('.leg-block').forEach((block, idx) => {
    const kind   = document.getElementById(`strike_kind_${idx}`)?.value;
    if (kind !== 'OTM') return;

    const sel    = document.getElementById(`strike_target_${idx}`);
    const custom = document.getElementById(`strike_target_custom_${idx}`);
    if (!sel) return;

    // If user chose custom, push the number into the select so backend gets a real value
    if (sel.value === '__custom__' && custom && custom.value.trim() !== '') {
      // Write the number into a hidden input named strike_target[]
      // (or just overwrite the select value if you prefer)
      sel.value = custom.value.trim();
    }
  });

  
  form.querySelectorAll('input[name^="entry_conditions_json_"], input[name^="exit_conditions_json_"]')
      .forEach(n => n.remove());

  // 2) Serialize current DOM -> hidden inputs
  const legBlocks = document.querySelectorAll('.leg-block');
  legBlocks.forEach((_, idx) => {
    const entry = extractConditions(document.getElementById(`entry_conditions_${idx}`));
    const exit  = extractConditions(document.getElementById(`exit_conditions_${idx}`));

    const entryInput = document.createElement('input');
    entryInput.type = 'hidden';
    entryInput.name = `entry_conditions_json_${idx}`;
    entryInput.value = JSON.stringify(entry);
    form.appendChild(entryInput);

    const exitInput = document.createElement('input');
    exitInput.type = 'hidden';
    exitInput.name = `exit_conditions_json_${idx}`;
    exitInput.value = JSON.stringify(exit);
    form.appendChild(exitInput);
  });
});

$(function () {
  $(document).on('mouseenter', '.constant-builder', function () {
    $(this).sortable({
      axis: 'x',
      items: '> .constant-item',
      handle: '.handle',
      placeholder: 'drag-placeholder',
      tolerance: 'pointer'
    });
  });
});

function restoreLegTargetUDV(idx, leg) {
  // ensure options exist
  if (typeof refreshStrikeTargetUDVOptionsFor === 'function') {
    refreshStrikeTargetUDVOptionsFor(idx);
  }

  if (leg.strike_kind !== 'OTM') return;

  const sel = document.getElementById(`strike_target_${idx}`);
  const custom = document.getElementById(`strike_target_custom_${idx}`);
  const names = (typeof getUDVNames === 'function') ? getUDVNames() : [];

  if (!sel) return;

  if (names.includes(leg.strike_target)) {
    sel.value = leg.strike_target;
    if (custom) { custom.style.display = 'none'; custom.value = ''; }
  } else if (!isNaN(parseFloat(leg.strike_target))) {
    sel.value = "__custom__";
    if (custom) { custom.style.display = ''; custom.value = String(leg.strike_target); }
  } else {
    // fallback: if no UDVs yet, leave blank; event will try again
    sel.value = "";
    if (custom) { custom.style.display = 'none'; custom.value = ''; }
  }
}




document.addEventListener("DOMContentLoaded", function () {
  const algoNameInput = document.getElementById("AlgoName");
  const fundInput = document.getElementById("MinimumFund");
  const defineBtn = document.getElementById("defineStrategyBtn");

  const feedback = document.getElementById("algoNameError");
  const fundFeedback = document.getElementById("fundError");

  function validateFields() {
    const name = algoNameInput.value.trim();
    const fund = fundInput.value.trim();

    fundFeedback.style.display = fund ? "none" : "block";
    defineBtn.disabled = !name || !fund;

    if (!name) {
      feedback.textContent = "Algorithm name is required.";
      feedback.style.display = "block";
      algoNameInput.classList.add("is-danger");
      return;
    }

    
  }

  // Attach validation listeners
  algoNameInput.addEventListener("input", validateFields);
  fundInput.addEventListener("input", validateFields);


   if (window.isEditMode) {
     const legsFromServer = Array.isArray(window.initialLegs) ? window.initialLegs : initialLegs;
 
     legsFromServer.forEach((leg, idx) => {
       addLeg();
 toggleStrikeMode(idx);
      const legBlock = document.querySelectorAll('.leg-block')[idx];

      // 1) Segment first
      const segSel = document.getElementById(`segment_${idx}`);
      if (segSel) {
        segSel.value = leg.exchange_segment || 'NFO';
        onSegmentChange(idx);
      }

      // 2) Instrument
      const instSel = document.getElementById(`instrument_${idx}`);
      if (instSel) {
        $(instSel).val(leg.instrument_name).trigger('change'); // keep Select2 behavior
      }

      setTimeout(() => {
        // 3) Expiry/Strike
        const exEl = document.getElementById(`expiry_${idx}`);
        const stEl = document.getElementById(`strike_${idx}`);
        if (exEl) exEl.value = leg.expiry_date || '';
        if (stEl) stEl.value = leg.strike_price || '';

        // 4) Lot sizing
        const lotSizeEl = document.getElementById(`lot_size_${idx}`);
        if (lotSizeEl) lotSizeEl.value = leg.lot_size_snapshot || '';
        const lotQtyEl = legBlock.querySelector(`input[name='lot_qty[]']`);
        if (lotQtyEl) lotQtyEl.value = leg.lot_qty || 1;

        // 5) Strike mode/target
const kindSel = document.getElementById(`strike_kind_${idx}`);
if (kindSel) { kindSel.value = leg.strike_kind || 'ABS'; toggleStrikeMode(idx); }
// initial attempt (works if UDVs already loaded)
restoreLegTargetUDV(idx, leg);
        // 6) Other dropdowns
        legBlock.querySelector(`select[name='option_type[]']`).value = leg.option_type;
        legBlock.querySelector(`select[name='order_direction[]']`).value = leg.order_direction;
        legBlock.querySelector(`select[name='order_type[]']`).value = leg.order_type;

        // 7) Conditions (unchanged)
        restoreConditionTree(`entry_conditions_${idx}`, leg.entry_conditions);
        restoreConditionTree(`exit_conditions_${idx}`, leg.exit_conditions);
      }, 300);
     });
   }


});


function initSelect2(element, placeholder = "Search...") {
  if (typeof $ !== 'undefined' && typeof $.fn.select2 !== 'undefined') {
    $(element).select2({
      width: 'resolve',
      placeholder: placeholder,
      allowClear: true,
      minimumInputLength: 1,
      ajax: {
        delay: 200,
        transport: function (params, success, failure) {
          const query = (params.data.q || '').toLowerCase().replace(/[^a-z0-9]/gi, '');
          if (!query) {
            success({ results: [] });
            return;
          }

          const matches = all_symbols
            .map(sym => {
              const normalized = sym.toLowerCase().replace(/[^a-z0-9]/gi, '');
              return {
                original: sym,
                score: fuzzyMatchScore(normalized, query)
              };
            })
            .filter(item => item.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, 50)
            .map(item => ({
              id: item.original,
              text: item.original
            }));

          success({ results: matches });
        }
      }
    });
  } else {
    console.error("Select2 or jQuery not available.");
  }
}

function showVarInUseModal() {
  document.getElementById("varInUseModal").classList.add("is-active");
}

function closeVarInUseModal() {
  document.getElementById("varInUseModal").classList.remove("is-active");

  // Optional: remove highlight after modal close
  document.querySelectorAll('.condition-row.highlight-red').forEach(el => {
    el.classList.remove('highlight-red');
  });
}

document.addEventListener("DOMContentLoaded", preloadUserDefinedVariables);

// Retry restoring Target after UDVs are (re)loaded
document.addEventListener('udv:changed', () => {
  if (!window.isEditMode) return;
  const legsFromServer = Array.isArray(window.initialLegs) ? window.initialLegs : window.initialLegs || [];
  legsFromServer.forEach((leg, idx) => restoreLegTargetUDV(idx, leg));
});
