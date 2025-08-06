instruments         = window.instruments;
indicators          = window.indicators;
all_symbols         = window.all_symbols;

let userDefinedVariables  = [];

// if we’re in edit mode, user-vars-data was already rendered in the template
if (window.isEditMode) {
  const userVarsEl = document.getElementById("user-vars-data");
  if (userVarsEl) {
    try {
      userDefinedVariables = JSON.parse(userVarsEl.textContent);
    } catch (e) {
      console.error("Failed to parse user-vars-data:", e);
    }
  }
}

// 3. Your existing helpers
const legs = JSON.parse(document.getElementById("legs-data").textContent);

function fuzzyMatchScore(symbol, query) {
  if (!query || !symbol) return 0;
  if (symbol.includes(query)) return 100;  // strong match
  let score = 0;
  let lastIndex = -1;
  for (let i = 0; i < query.length; i++) {
    const char = query[i];
    const index = symbol.indexOf(char, lastIndex + 1);
    if (index === -1) return 0;
    score += 10 - (index - lastIndex);  // closer is better
    lastIndex = index;
  }
  return score;
}
function formatDropdownItem(data) {
  if (!data.id) return data.text;

  const isUserVar = data.text.includes("(User Var)");
  const parent = data.element?.parentElement?.label || "";

  // Format optgroup label items
  if (!data.element || !data.element.value) return data.text;

  const style = parent === "User Defined"
    ? 'color: #1b5e20; font-weight: 600;'
    : 'color: #004085; font-weight: 600;';

  const text = isUserVar ? `<span style="margin-left: 6px;">${data.text}</span>` : data.text;

  return $(`<span style="${style} font-size: 13px;">${text}</span>`);
}

function getAllVariableOptionsHTML() {
  const grouped = {};
  indicators.forEach(v => {
    const cat = v.category || "uncategorized";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(v);
  });

  const categoryNames = Object.keys(grouped).sort();
  let html = `<option value="">-- Select Variable --</option>`;

  categoryNames.forEach(cat => {
    const sorted = grouped[cat].sort((a, b) => a.display_name.localeCompare(b.display_name));
    html += `<optgroup label="${cat}">`;
    sorted.forEach(v => {
      html += `<option value="${v.name}">${v.display_name}</option>`;
    });
    html += `</optgroup>`;
  });

  const sortedUserVars = [...userDefinedVariables].sort((a, b) => a.name.localeCompare(b.name));
  if (sortedUserVars.length > 0) {
    html += `<optgroup label="User Defined">`;
    sortedUserVars.forEach(v => {
      html += `<option value="${v.name}">${v.name}</option>`;
    });
    html += `</optgroup>`;
  }

  return html;
}

function buildVariableDropdown(index) {
  // Group indicators by category
  const grouped = {};
  indicators.forEach(v => {
    const cat = v.category || "uncategorized";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(v);
  });

  const categoryNames = Object.keys(grouped).sort();
  let dropdownHtml = `<option value="">-- Select Variable --</option>`;

  categoryNames.forEach(cat => {
    const sorted = grouped[cat].sort((a, b) => a.display_name.localeCompare(b.display_name));
    dropdownHtml += `<optgroup label="${cat}">`;
    sorted.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.display_name}</option>`;
    });
    dropdownHtml += `</optgroup>`;
  });

  // Show all user-defined vars (not index-limited anymore)
  const sortedUserVars = [...userDefinedVariables].sort((a, b) => a.name.localeCompare(b.name));
  if (sortedUserVars.length > 0) {
    dropdownHtml += `<optgroup label="User Defined">`;
    sortedUserVars.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.name} (User Var)</option>`;
    });
    dropdownHtml += `</optgroup>`;
  }

  return dropdownHtml;
}

function showStrategySection() {
  const name = document.getElementById("AlgoName").value.trim();
  const fund = document.getElementById("MinimumFund").value.trim();

  if (name && fund) {
    document.getElementById("strategySection").style.display = "block";
    document.getElementById("defineStrategyBtn").disabled = true;
   // document.getElementById("basicDetailsSection").querySelectorAll("input, textarea").forEach(el => el.disabled = true);
  } else {
    document.getElementById("algoNameError").style.display = name ? "none" : "block";
    document.getElementById("fundError").style.display = fund ? "none" : "block";
  }
}

