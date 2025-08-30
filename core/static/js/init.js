document.addEventListener('change', function (e) {
  if (!e.target.classList.contains('rhs-mode')) return;
  const row = e.target.closest('.condition-row');
  const isVar = e.target.value === 'variable';
  row.querySelector('.condition-value').style.display = isVar ? 'none' : '';
  const rhs = row.querySelector('.rhs-input');
  if (rhs) rhs.style.display = isVar ? 'inline-flex' : 'none';
});



form.addEventListener("submit", function (e) {
  let hasError = false;

  // Normalize + validate + ensure hidden inputs for strike_target[]
  document.querySelectorAll('.leg-block').forEach((block, idx) => {
    const kind   = document.getElementById(`strike_kind_${idx}`)?.value;
    const sel    = document.getElementById(`strike_target_${idx}`);
    const custom = document.getElementById(`strike_target_custom_${idx}`);
    if (!sel) return;

    let finalValue = "";
    if (kind === "OTM") {
      if (sel.value === "__custom__" && custom?.value.trim() !== "") {
        finalValue = custom.value.trim();
        sel.value = finalValue;  
      } else {
        finalValue = sel.value || "";
      }

      // 🔍 Validation
      if (!finalValue) {
        alert(`Leg ${idx + 1}: OTM target must be provided`);
        hasError = true;
      } else if (!( /^\d+$/.test(finalValue) || /^[A-Za-z_][A-Za-z0-9_]*$/.test(finalValue) )) {
        alert(`Leg ${idx + 1}: OTM target must be a number or a valid variable name`);
        hasError = true;
      }
    }

    // ✅ Ensure hidden strike_target[] field always present
    let hidden = block.querySelector("input[type=hidden][name='strike_target[]']");
    if (!hidden) {
      hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "strike_target[]";
      block.appendChild(hidden);
    }
    hidden.value = finalValue;
  });

  if (hasError) {
    e.preventDefault(); // stop submit if any error
    return false;
  }

  // Remove prior hidden inputs for rules
  form.querySelectorAll('input[name="rules_json"]').forEach(n => n.remove());

  const rules = [];
  const legBlocks = document.querySelectorAll(".leg-block");
  legBlocks.forEach((block, idx) => {
    const legId = block.dataset.legId || null;

    [
      {type: "ENTRY", el: `entry_conditions_${idx}`, action: "PLACE_ORDER"},
      {type: "EXIT", el: `exit_conditions_${idx}`, action: "CLOSE_POSITION"},
      {type: "REPAIR", el: `repair_conditions_${idx}`, action: "MODIFY_ORDER"},
      {type: "UNIVERSAL_EXIT", el: `universal_exit_conditions_${idx}`, action: "CLOSE_ALL"}
    ].forEach(cfg => {
      const condEl = document.getElementById(cfg.el);
      if (!condEl) return;

      const tree = extractConditions(condEl);
      if (!tree || !tree.conditions || tree.conditions.length === 0) return;

      rules.push({
        leg_index: idx,
        leg_id: legId,
        rule_type: cfg.type,
        scope: cfg.type === "UNIVERSAL_EXIT" ? "ALGO" : "LEG",
        trigger_event: "ON_CONDITION",
        priority: cfg.type === "UNIVERSAL_EXIT" ? 10 : 50,
        condition_tree: tree,
        action_type: cfg.action,
        action_params: {},
        policy: { repeatable: true }
      });
    });
  });

  // Append one hidden input with all rules
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "rules_json";
  input.value = JSON.stringify(rules);
  form.appendChild(input);
});   // ✅ only this one closes the addEventListener


window.restoreLegTargetUDV=function (idx, leg) {
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
  const strategySection = document.getElementById("strategySection");
if (strategySection) {
  strategySection.style.display = "block";
  strategySection.classList.remove("is-hidden"); // if using Bulma
}

const defineBtn = document.getElementById("defineStrategyBtn");
if (defineBtn) {
  defineBtn.style.display = "none"; // optional: hide the button in edit mode
}

    const legsFromServer = Array.isArray(window.Legs) ? window.Legs : Legs;

    // --- Restore legs ---
    legsFromServer.forEach((leg, idx) => {
      addLeg();
      toggleStrikeMode(idx);
      const legBlock = document.querySelectorAll('.leg-block')[idx];

      // 1) Segment
      const segSel = document.getElementById(`segment_${idx}`);
      if (segSel) {
        segSel.value = leg.exchange_segment || 'NFO';
        onSegmentChange(idx);
      }

      // 2) Instrument
      restoreInstrument(idx, leg.instrument_name);

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
        if (kindSel) {
          kindSel.value = leg.strike_kind || 'ABS';
          toggleStrikeMode(idx);
        }
         if (typeof restoreLegTargetUDV === 'function') {
            restoreLegTargetUDV(idx, leg);
            }
        // 6) Other dropdowns
        legBlock.querySelector(`select[name='option_type[]']`).value = leg.option_type;
        legBlock.querySelector(`select[name='order_direction[]']`).value = leg.order_direction;
        legBlock.querySelector(`select[name='order_type[]']`).value = leg.order_type;

        // 7) (conditions restored separately below)
      }, 500);
    }); // ✅ close forEach here

    // --- Restore rules (outside forEach, run once) ---
     setTimeout(() => {if (Array.isArray(window.initialRules)) {
      window.initialRules.forEach(rule => {
        let legIndex = 0;
if (rule.scope === "LEG") {
  if (rule.leg_index != null) {
    legIndex = rule.leg_index;
  } else if (rule.leg_id) {
    legIndex = window.Legs.findIndex(l => l.id === rule.leg_id);
    if (legIndex === -1) legIndex = 0;
  }
}

        let containerId = null;

        switch (rule.rule_type) {
          case "ENTRY": containerId = `entry_conditions_${legIndex}`; break;
          case "EXIT": containerId = `exit_conditions_${legIndex}`; break;
          case "REPAIR": containerId = `repair_conditions_${legIndex}`; break;
          case "UNIVERSAL_EXIT": containerId = `universal_exit_conditions_${legIndex}`; break;
        }

        if (containerId && rule.condition_tree) {
         const tree = rule.condition_tree;
          restoreConditionTree(containerId, tree.conditions || [], tree.connector || "AND");
        }
      });
    }
  },500);
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
  const legsFromServer = Array.isArray(window.Legs) ? window.Legs : window.Legs || [];
  legsFromServer.forEach((leg, idx) => restoreLegTargetUDV(idx, leg));
});

function restoreInstrument(idx, symbol, retries = 5) {
  const instSel = document.getElementById(`instrument_${idx}`);
  if (!instSel) return;

  const optExists = [...instSel.options].some(o => o.value === symbol);
  if (optExists) {
    $(instSel).val(symbol).trigger('change');
    console.log(`Instrument restored for leg ${idx}:`, symbol);
  } else if (retries > 0) {
    console.log(`Retrying instrument restore for leg ${idx}...`);
    setTimeout(() => restoreInstrument(idx, symbol, retries - 1), 200);
  } else {
    console.warn(`Failed to restore instrument for leg ${idx}:`, symbol);
  }
}
