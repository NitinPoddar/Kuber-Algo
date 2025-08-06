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
  // 1. Show strategy section immediately
  document.getElementById("strategySection").style.display = "block";
  document.getElementById("defineStrategyBtn").style.display = "none";

  // 2. Pre-fill top fields
  //algoNameInput.value = "{{ algo.algo_name|escapejs }}";
  //fundInput.value = "{{ algo.minimum_fund_reqd|default:'' }}";
  //document.querySelector("textarea[name='Algo_description']").value = `{{ algo.algo_description|escapejs }}`;
  defineBtn.disabled = false;

  // 3. Load user-defined variables (already available globally)
  preloadUserDefinedVariables();

  // 4. Load legs from parsed JSON
  let legs = [];
  const legsEl = document.getElementById("legs-data");
  if (legsEl) {
    try {
      legs = JSON.parse(legsEl.textContent);
    } catch (e) {
      console.error("❌ Error parsing legs-data:", e);
    }
  }

  // 5. Add legs and populate
  legs.forEach((leg, idx) => {
    addLeg();
    const legBlock = document.querySelectorAll('.leg-block')[idx];
    const select = legBlock.querySelector(`.instrument-dropdown`);

    // Set instrument
    $(select).val(leg.instrument_name).trigger('change');

    setTimeout(() => {
      // Set expiry and strike
      document.getElementById(`expiry_${idx}`).value = leg.expiry_date || '';
      document.getElementById(`strike_${idx}`).value = leg.strike_price || '';

      // Set other dropdowns
      legBlock.querySelector(`select[name='option_type[]']`).value = leg.option_type;
      legBlock.querySelector(`select[name='order_direction[]']`).value = leg.order_direction;
      legBlock.querySelector(`select[name='order_type[]']`).value = leg.order_type;

      // Add and restore conditions
      addRootCondition(`entry_conditions_${idx}`, legBlock.querySelector(`#entry_conditions_${idx} + button`));
      restoreConditionTree(`entry_conditions_${idx}`, leg.entry_conditions);

      addRootCondition(`exit_conditions_${idx}`, legBlock.querySelector(`#exit_conditions_${idx} + button`));
      restoreConditionTree(`exit_conditions_${idx}`, leg.exit_conditions);
    }, 300); // delay ensures DOM is ready
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

document.addEventListener('change', e => {
  if (!e.target.matches('select.rhs-mode')) return;
  const sel     = e.target;
  const row     = sel.closest('.condition-row');
  const textIn  = row.querySelector('input.condition-value');
  const varDiv  = row.querySelector('div.rhs-input');

  const isValue = sel.value === 'value';
  textIn.style.display   = isValue ? ''     : 'none';
  varDiv.style.display   = isValue ? 'none' : '';

  if (!isValue) {
    const varSel = varDiv.querySelector('select.rhs-variable-dropdown');
    renderConditionVariableParams(varSel);
  }
});
