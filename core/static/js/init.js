form.addEventListener("submit", function(e) {
  const legs = document.querySelectorAll('.leg-block');
  legs.forEach((leg, idx) => {
    const entry = extractConditions(document.getElementById(`entry_conditions_${idx}`));
    const exit = extractConditions(document.getElementById(`exit_conditions_${idx}`));
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
    const legs = Array.isArray(window.legs) ? window.legs : [];

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



