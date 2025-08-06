# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 23:18:49 2025

@author: Home
"""

<!-- Simplified add_algo.html Template with Single Flat Condition Structure -->
{% extends 'core/base.html' %}
{% load static %}

{% block content %}




 <html lang="en">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Add Algo{% endblock %}</title>

  <!-- Bulma CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.3/css/bulma.min.css">

  <!-- Select2 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />

  <!-- Optional Font -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">

  <!-- Your custom styles -->
  <link rel="stylesheet" href="{% static 'css/style.css' %}">

  <!-- jQuery (Only Once) -->
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

  <!-- jQuery UI (for drag/drop) -->
  <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"></script>

  <!-- Select2 JS -->
  <script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>

<body>

{{ legs_json|json_script:"legs-data" }}
{{ user_vars_json|json_script:"user-vars-data" }}

<section class="section">
  <div class="container">
    <h1 class="title">{% if is_edit_mode %}Edit Algorithm: {{ algo.algo_name }}{% else %}Add New Algorithm{% endif %}</h1>

    
<form id="algoForm" method="post" action="{% if is_edit_mode %}{% url 'edit_algo' algo.id %}{% else %}{% url 'add_algo' %}{% endif %}">

  {% csrf_token %}

  <!-- SECTION 1 -->
  <div id="basicDetailsSection">
    <div class="field">
      <label class="label">Algorithm Name <span class="has-text-danger">*</span></label>
      <input class="input" type="text" name="AlgoName" id="AlgoName"
       value="{{ algo.algo_name|default:'' }}" required>
      <p class="help is-danger" id="algoNameError" style="display: none;">Algorithm name is required.</p>
    </div>

    <div class="field">
      <label class="label">Minimum Fund Required <span class="has-text-danger">*</span></label>
      <input class="input" type="number" name="Minimum_Fund_Reqd" id="MinimumFund"
       value="{{ algo.minimum_fund_reqd|default:'' }}" required>
      <p class="help is-danger" id="fundError" style="display: none;">Minimum fund is required.</p>
    </div>

    <div class="field">
      <label class="label">Description</label>
      <textarea class="textarea" name="Algo_description" id="Algo_description">{{ algo.algo_description|default:'' }}</textarea>
    </div>

    <div class="field mt-4">
      <button type="button" class="button is-primary" id="defineStrategyBtn" disabled onclick="showStrategySection()">🚀 Define Strategy</button>
    </div>
  </div>

  <!-- SECTION 2: Initially Hidden -->
  <div id="strategySection" style="display: none;">
    <hr>

    <div class="field">
      <label class="label">Define Variables (User-Defined Variables)</label>
      <div id="userConstantsContainer"></div>
      <button type="button" class="button is-small is-info mt-2" onclick="addUserDefinedVariable()">➕ Add Variable</button>
    </div>

    <hr>
    <div id="legsContainer"></div>

    <div class="field mt-4">
      <button type="button" class="button is-primary" onclick="addLeg()">➕ Add Leg</button>
    </div>

    <div class="field mt-4">
      <button type="button" class="button is-info" onclick="showPreview()">👁️ Preview</button>
      <button type="submit" class="button is-success ml-2">✅ Confirm & Submit</button>
    </div>
  </div>
</form>

<p id="const_preview_${index}" class="is-size-7 has-text-grey mt-1 ml-1"></p>

<div class="box mt-5" id="jsonPreviewBox" style="display:none">
  <h2 class="subtitle">🧾 JSON Preview</h2>
  <pre><code id="jsonPreview"></code></pre>
  <h2 class="subtitle mt-3">🐍 Python Preview</h2>
  <pre><code id="pythonPreview"></code></pre>
</div>
<style>
  .nested-condition {
    border-left: 2px solid #7a7a7a;
    margin-left: 1rem;
    padding-left: 1rem;
    position: relative;
  }
  .nested-condition::before {
    content: "";
    position: absolute;
    left: -1.4rem;
    top: 50%;
    transform: translateY(-50%);
    width: 1.4rem;
    height: 2px;
    background-color: #7a7a7a;
  }
  .condition-row {
    position: relative;
    margin-left: 1.5rem;
  }
  .condition-row::before {
    content: "";
    position: absolute;
    top: 50%;
    left: -1.4rem;
    transform: translateY(-50%);
    width: 1.2rem;
    height: 1px;
    background-color: #9999ff;
  }
  
   .constant-item .handle::before {
    content: '\2630'; /* ☰ */
    margin-right: 5px;
    cursor: move;
    color: #777;
  }

    .select2-container {
      min-width: 100%;
      width: 100% !important;
    }
    #userConstantsContainer .expression_builder {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: flex-start;
}

.condition-row.highlight-red {
  border: 2px dashed red;
  background-color: #fff0f0;
}


#userConstantsContainer .is-size-7 {
  font-style: italic;
  background-color: #f4f4f4;
  padding: 0.25rem 0.5rem;
  border-left: 3px solid #00c4a7;
}

#userConstantsContainer .field,
#userConstantsContainer .expression_builder,
#userConstantsContainer .buttons {
  transition: all 0.3s ease;
}

</style>

<div class="modal" id="varInUseModal">
  <div class="modal-background"></div>
  <div class="modal-card">
    <header class="modal-card-head">
      <p class="modal-card-title">Cannot Delete Variable</p>
      <button class="delete" aria-label="close" onclick="closeVarInUseModal()"></button>
    </header>
    <section class="modal-card-body">
      <p class="has-text-danger">❌ This variable is currently being used in one or more condition rows.</p>
      <p>Please remove it from those rows before deleting.</p>
    </section>
    <footer class="modal-card-foot">
      <button class="button" onclick="closeVarInUseModal()">OK</button>
    </footer>
  </div>
</div>


<script>
const instruments = {{ instruments_json|safe }};
const indicators = {{ indicators_json|safe }};
const all_symbols = {{ symbol_list_json|safe }}; // ✅ Now available globally

//const userDefinedVariables = {{ user_vars_json|safe }};

let userDefinedVariables = [];

{% if is_edit_mode %}
const userVarsEl = document.getElementById("user-vars-data");
if (userVarsEl) {
  try {
    userDefinedVariables = JSON.parse(userVarsEl.textContent);
  } catch (e) {
    console.error("❌ Failed to parse user-vars-data:", e);
  }
}
{% endif %}

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

function loadExpressionUIFromJSON(containerId, expressionData) {
  const container = document.getElementById(containerId);
  if (!container || !Array.isArray(expressionData)) return;

  container.innerHTML = ''; // Clear any previous content

  expressionData.forEach((part, idx) => {
    let elementWrapper = document.createElement('div');
    elementWrapper.classList.add('control');

    // ➕ Variable
    if (part.type === 'variable') {
      const select = document.createElement('select');
      select.classList.add('select', 'is-small', 'expression-part');
      select.dataset.partType = 'variable';

      const emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'Select Variable';
      select.appendChild(emptyOpt);

      userDefinedVariables.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = v.name;
        if (v.name === part.value) opt.selected = true;
        select.appendChild(opt);
      });

      elementWrapper.appendChild(select);
    }

    // ➕ Operator
    else if (part.type === 'operator') {
      const input = document.createElement('input');
      input.classList.add('input', 'is-small', 'expression-part');
      input.placeholder = 'Operator';
      input.dataset.partType = 'operator';
      input.value = part.value || '';
      elementWrapper.appendChild(input);
    }

    // ➕ Value
    else if (part.type === 'value') {
      const input = document.createElement('input');
      input.classList.add('input', 'is-small', 'expression-part');
      input.placeholder = 'Value';
      input.dataset.partType = 'value';
      input.value = part.value || '';
      elementWrapper.appendChild(input);
    }

    // ➕ Constant (Read-only label)
    else if (part.type === 'constant') {
      const span = document.createElement('span');
      span.classList.add('tag', 'is-info');
      span.textContent = part.value || '[constant]';
      elementWrapper.appendChild(span);
    }

    // Add to container
    container.appendChild(elementWrapper);
  });
}

function buildExpressionFromUI(index) {
  const container = document.getElementById(`expression_builder_${index}`);
  const parts = [];

  container.querySelectorAll('.expression-part').forEach(el => {
    const type = el.dataset.partType;
    const value = el.value?.trim();

    if (value) {
      parts.push({ type, value });
    }
  });

  return parts;
}

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

function renderConditionVariableParams(selectEl) {
  const variableName = selectEl.value;
  const container = selectEl.closest('.condition-row');
  const paramDiv = container.querySelector('.condition-parameters');
  paramDiv.innerHTML = '';

  if (!variableName) return;

  // Search in both indicators and userDefinedVariables
  const variable =
    indicators.find(i => i.name === variableName) ||
    userDefinedVariables.find(v => v.name === variableName);

  if (!variable) {
    const warning = document.createElement('div');
    warning.className = 'has-text-danger has-text-weight-semibold';
    warning.textContent = "⚠️ Unknown variable selected.";
    paramDiv.appendChild(warning);
    return;
  }

  if (!variable.parameters || variable.parameters.length === 0) {
    const msg = document.createElement('div');
    msg.className = 'has-text-grey-light is-size-7 is-italic mt-1';
    msg.textContent = 'No parameters required.';
    paramDiv.appendChild(msg);
    return;
  }

  // Render required inputs
  variable.parameters.forEach(param => {
    if (param.name.toLowerCase() === 'symbol') {
      const selectId = `cond_symbol_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      const select = document.createElement('select');
      select.name = `cond_param_${variableName}_${param.name}`;
      select.id = selectId;
      select.className = 'symbol-dropdown input is-small mt-1';
      paramDiv.appendChild(select);
      initSelect2(`#${selectId}`, "Select symbol");
    } else {
      const input = document.createElement('input');
      input.className = 'input is-small mt-1';
      input.placeholder = param.name;
      input.name = `cond_param_${variableName}_${param.name}`;
      input.value = param.default_value || "";
      paramDiv.appendChild(input);
    }
  });
}


  function renderInlineVariableParams(selectEl, index) {
    const variableName = selectEl.value;
    const paramTarget = selectEl.closest('.field').querySelector('.parameters');
    paramTarget.innerHTML = '';

    const variable = indicators.find(i => i.name === variableName);
    if (!variable || !variable.parameters) return;

    variable.parameters.forEach(param => {
      if (param.name.toLowerCase() === 'symbol') {
        const symbolSelectId = `symbol_select_${index}_${Date.now()}`;
        const symbolDropdown = document.createElement('select');
        symbolDropdown.name = `const_expr_${index}_${variable.name}_${param.name}`;
        symbolDropdown.className = 'symbol-dropdown select is-small mt-1';
        symbolDropdown.id = symbolSelectId;
        paramTarget.appendChild(symbolDropdown);
        initSelect2(`#${symbolSelectId}`, "Select symbol");
      } else {
        const input = document.createElement('input');
        input.className = 'input is-small mt-1';
        input.placeholder = `${param.name}`;
        input.name = `const_expr_${index}_${variable.name}_${param.name}`;
        paramTarget.appendChild(input);
      }
    });
  }



function validateExpressionBuilder(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const items = target.querySelectorAll('.expression-item');
  const errors = [];

  const statusIcon = document.getElementById(`constant_status_${index}`);
  const previewEl = document.getElementById(`const_preview_${index}`);

  const parts = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    // Validation Rules
    if (i === 0 && isOperator) {
      errors.push("❌ Expression cannot start with an operator.");
    }
    if (i === items.length - 1 && isOperator) {
      errors.push("❌ Expression cannot end with an operator.");
    }

    if ((isValue || isVariable) && i < items.length - 1) {
      const nextItem = items[i + 1];
      const nextIsValue = nextItem.querySelector('input') && !nextItem.querySelector('.inline-variable-dropdown');
      const nextIsVariable = nextItem.querySelector('.inline-variable-dropdown');
      if (nextIsValue || nextIsVariable) {
        errors.push("❌ Operator required between two values/variables.");
      }
    }

    // Build preview part
    if (isVariable) {
      const varName = isVariable.value;
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      const paramParts = [];

      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) {
          paramParts.push(`${key}=${p.value}`);
        }
      });

      parts.push(`${varName}(${paramParts.join(', ')})`);
    } else if (isOperator) {
      parts.push(item.querySelector('select').value);
    } else if (isValue) {
      const val = item.querySelector('input').value;
      if (val) parts.push(val);
    }
  }

  // Formula Preview
  if (previewEl) {
    previewEl.textContent = parts.join(' ');
  }

  // Validation Icon
  if (statusIcon) {
    statusIcon.innerHTML = errors.length === 0
      ? `<i class="has-text-success">✅</i>`
      : `<i class="has-text-danger">❌</i>`;
  }

  // Error Box
  let errorBox = document.getElementById(`expr_error_box_${index}`);
  if (!errorBox) {
    errorBox = document.createElement('div');
    errorBox.id = `expr_error_box_${index}`;
    errorBox.className = "notification is-danger is-light mt-2";
    target.parentElement.appendChild(errorBox);
  }

  errorBox.style.display = errors.length ? 'block' : 'none';
  errorBox.innerHTML = errors.length
    ? `<strong>Validation Error:</strong><ul>${errors.map(e => `<li>${e}</li>`).join('')}</ul>`
    : '';
}

function addUserDefinedVariable() {
  const container = document.getElementById('userConstantsContainer');
  const index = container.children.length;

  const box = document.createElement('div');
  box.classList.add('box', 'mb-3');
  box.id = `user_constant_box_${index}`;
  box.innerHTML = `
    <div class="is-flex is-justify-content-space-between is-align-items-center mb-2">
      <strong>Variable Definition</strong>
      <div class="is-flex is-align-items-center">
        <span id="constant_status_${index}" class="icon is-small mr-2"></span>
        <button id="user_variable_close_${index}" type="button" class="delete" onclick="removeUserConstant(${index})"></button>
      </div>
    </div>

    <div class="field">
      <label class="label">Variable Name</label>
      <input class="input" name="user_constant_name_${index}" placeholder="e.g., Variable1" data-original-name="">
      <p id="var_name_error_${index}" class="help is-danger" style="display:none;"></p>
    </div>

    <div id="expression_builder_${index}" class="is-flex is-align-items-center is-flex-wrap-wrap mb-3"></div>
    <p id="const_preview_${index}" class="is-size-7 has-text-grey mt-1 ml-1"></p>

    <div class="buttons mb-2">
      <button type="button" class="button is-small is-primary" onclick="addExpressionVariable(${index})">➕ Variable</button>
      <button type="button" class="button is-small is-info" onclick="addExpressionOperator(${index})">➕ Operator</button>
      <button type="button" class="button is-small is-link" onclick="addExpressionValue(${index})">➕ Value</button>
    </div>

    <button type="button" class="button is-small is-success" onclick="saveUserConstant(${index})">💾 Save Variable</button>
  `;

  container.appendChild(box);
box.querySelector(`input[name="user_constant_name_${index}"]`).dataset.originalName = "";

  // Add real-time validation on name input
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const errorText = box.querySelector(`#var_name_error_${index}`);

  nameInput.addEventListener("input", function () {
  const name = nameInput.value.trim();
  const allInputs = document.querySelectorAll('input[name^="user_constant_name_"]');
  let duplicate = false;

  for (const inp of allInputs) {
    if (inp !== nameInput && inp.value.trim() === name) {
      duplicate = true;
      break;
    }
  }

  const existsInPredefined = userDefinedVariables.some(v => v.name === name);
  const errorText = document.getElementById(`var_name_error_${index}`);
  const saveBtn = document.querySelector(`#user_constant_box_${index} button[onclick^="saveUserConstant"]`);

  if (!name) {
    nameInput.classList.add("is-danger");
    errorText.textContent = "Variable name cannot be empty.";
    errorText.style.display = "block";
    if (saveBtn) saveBtn.disabled = true;
  } else if (duplicate || existsInPredefined) {
    nameInput.classList.add("is-danger");
    errorText.textContent = "Variable name already exists.";
    errorText.style.display = "block";
    if (saveBtn) saveBtn.disabled = true;
  } else {
    nameInput.classList.remove("is-danger");
    errorText.style.display = "none";
    errorText.textContent = "";
    if (saveBtn) saveBtn.disabled = false;
  }
});

}
function updateUserVariableHiddenJSON(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const container = document.getElementById(`expression_builder_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();

  if (!name) return;

  const items = container.querySelectorAll('.expression-item');
  const expression = [];

  items.forEach(item => {
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    if (isVariable) {
      const varName = isVariable.value;
      const params = [];
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) params.push({ key, value: p.value });
      });
      expression.push({ type: 'variable', name: varName, parameters: params });
    } else if (isOperator) {
      const value = item.querySelector('select').value;
      expression.push({ type: 'operator', value });
    } else if (isValue) {
      const value = item.querySelector('input').value;
      expression.push({ type: 'value', value });
    }
  });

  // Update hidden input
  let hiddenInput = document.getElementById(`user_constant_input_${index}`);
  if (!hiddenInput) {
    hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = `user_variable_json_${index}`;
    hiddenInput.id = `user_constant_input_${index}`;
    document.getElementById("algoForm").appendChild(hiddenInput);
  }

  hiddenInput.value = JSON.stringify({ name, expression });
}

function saveUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const container = document.getElementById(`expression_builder_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();
  const closeBtn = document.getElementById(`user_variable_close_${index}`);
  const originalName = nameInput.getAttribute('data-original') || name;

  if (closeBtn) closeBtn.style.display = 'none';

  // Validate name
  const allInputs = document.querySelectorAll('input[name^="user_constant_name_"]');
  let duplicate = false;
  allInputs.forEach(inp => {
    if (inp !== nameInput && inp.value.trim() === name) duplicate = true;
  });

  const existsInPredefined = userDefinedVariables.some(v => v.name === name && name !== originalName);

  const errorText = document.getElementById(`var_name_error_${index}`);
  if (!name || (duplicate || existsInPredefined)) {
    nameInput.classList.add("is-danger");
    nameInput.title = !name ? "Variable name cannot be empty" : "Variable name already exists";
    if (errorText) {
      errorText.textContent = name ? "Variable name already exists" : "Variable name cannot be empty";
    }
    return;
  }

  nameInput.classList.remove("is-danger");
  nameInput.removeAttribute("title");
  if (errorText) errorText.textContent = "";

  // Expression builder logic
  const items = container.querySelectorAll('.expression-item');
  const expression = [];
  let formulaPreview = "";

  items.forEach(item => {
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    if (isVariable) {
      const varName = isVariable.value;
      const params = [];
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) params.push({ key, value: p.value });
      });
      expression.push({ type: 'variable', name: varName, parameters: params });
      formulaPreview += `${varName}(${params.map(p => `${p.key}=${p.value}`).join(', ')}) `;
    } else if (isOperator) {
      const value = item.querySelector('select').value;
      expression.push({ type: 'operator', value });
      formulaPreview += ` ${value} `;
    } else if (isValue) {
      const value = item.querySelector('input').value;
      expression.push({ type: 'value', value });
      formulaPreview += `${value} `;
    }
  });

  // Update hidden input
  let hiddenInput = document.getElementById(`user_constant_input_${index}`);
  if (!hiddenInput) {
    hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = `user_variable_json_${index}`;
    hiddenInput.id = `user_constant_input_${index}`;
    document.getElementById("algoForm").appendChild(hiddenInput);
  }
  hiddenInput.value = JSON.stringify({ name, expression });

  // UI updates
  const preview = document.getElementById(`const_preview_${index}`);
  if (preview) preview.style.display = 'none';

  const fieldBlocks = box.querySelectorAll('.field, .buttons, .expression_builder');
  fieldBlocks.forEach(el => el.style.display = 'none');

  const oldBtn = box.querySelector("button[onclick^='saveUserConstant']");
  if (oldBtn) oldBtn.remove();

  const summaryLine = document.createElement('div');
  summaryLine.id = `user_constant_summary_${index}`;
  summaryLine.className = 'mt-2 p-2 has-background-light has-text-weight-semibold';
  summaryLine.innerHTML = `<span class="has-text-grey-dark">${name} = ${formulaPreview.trim()}</span>`;
  box.appendChild(summaryLine);

  const actionWrapper = document.createElement("div");
  actionWrapper.className = "buttons mt-2";
  actionWrapper.id = `edit_delete_controls_${index}`;
  actionWrapper.innerHTML = `
    <button type="button" class="button is-small is-warning" onclick="editUserConstant(${index})">✏️</button>
    <button type="button" class="button is-small is-danger" onclick="removeUserConstant(${index})">🗑️</button>
  `;
  box.appendChild(actionWrapper);

  // Update global registry
  userDefinedVariables = userDefinedVariables.filter(v => v.name !== originalName);
  userDefinedVariables.push({ name, expression });

  // Update dropdowns
 // 🆕 Update all dropdowns with the latest user-defined variable list
const allDropdowns = document.querySelectorAll('.inline-variable-dropdown');
allDropdowns.forEach(dd => {
  const currentVal = dd.value; // preserve selected value
  dd.innerHTML = getAllVariableOptionsHTML();
  $(dd).val(currentVal).trigger('change.select2');  // update Select2
});

  // Persist to backend
 

  // Track saved name
  nameInput.setAttribute("data-original", name);
}

function editUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const summary = document.getElementById(`user_constant_summary_${index}`);
  const controls = document.getElementById(`edit_delete_controls_${index}`);
  const preview = document.getElementById(`const_preview_${index}`);
  const closeBtn = document.getElementById(`user_variable_close_${index}`);

  if (summary) summary.remove();
  if (controls) controls.remove();
  if (preview) preview.style.display = 'none';
  if (closeBtn) closeBtn.style.display = 'inline-block';

  const allFields = box.querySelectorAll('.field, .expression_builder, .buttons');
  allFields.forEach(el => el.style.display = '');

  const oldBtn = box.querySelector("button[onclick^='saveUserConstant']");
  if (oldBtn) oldBtn.remove();

  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.className = 'button is-small is-success';
  saveBtn.textContent = '💾 Save Variable';
  saveBtn.setAttribute('onclick', `saveUserConstant(${index})`);
  box.appendChild(saveBtn);

  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const originalName = nameInput.value.trim();
  nameInput.setAttribute('data-original', originalName);

  // Error box
  let errorText = document.getElementById(`var_name_error_${index}`);
  if (!errorText) {
    errorText = document.createElement("p");
    errorText.id = `var_name_error_${index}`;
    errorText.className = "help is-danger";
    nameInput.parentElement.appendChild(errorText);
  }

  // Revalidation
  nameInput.addEventListener("input", function () {
    const name = nameInput.value.trim();
    const allInputs = document.querySelectorAll('input[name^="user_constant_name_"]');
    let duplicate = false;
    for (const inp of allInputs) {
      if (inp !== nameInput && inp.value.trim() === name) {
        duplicate = true;
        break;
      }
    }

    const existsInPredefined = userDefinedVariables.some(v => v.name === name && name !== originalName);
    const isSameAsOriginal = name === originalName;

    if (!name) {
      nameInput.classList.add("is-danger");
      nameInput.title = "Variable name cannot be empty";
      errorText.textContent = "Variable name cannot be empty";
      saveBtn.disabled = true;
    } else if ((duplicate || existsInPredefined) && !isSameAsOriginal) {
      nameInput.classList.add("is-danger");
      nameInput.title = "Variable name already exists";
      errorText.textContent = "Variable name already exists";
      saveBtn.disabled = true;
    } else {
      nameInput.classList.remove("is-danger");
      nameInput.removeAttribute("title");
      errorText.textContent = "";
      saveBtn.disabled = false;
    }
  });

  nameInput.dispatchEvent(new Event("input"));  // Trigger validation immediately
}

function highlightConditionRowsUsing(varName) {
  document.querySelectorAll('.condition-variable').forEach(select => {
    const row = select.closest('.condition-row');
    if (select.value === varName && row) {
      row.classList.add('highlight-red');
    }
  });
}

function highlightUserVarsUsing(varName) {
  document.querySelectorAll('.expression-item').forEach(item => {
    const dropdown = item.querySelector('.inline-variable-dropdown');
    if (dropdown?.value === varName) {
      const row = item.closest('.expression_builder')?.closest('.box');
      if (row) row.classList.add('highlight-red');
    }
  });
}
function showModal(msg) {
  document.querySelector("#varInUseModal .modal-card-body").innerHTML = `
    <p class="has-text-danger">❌ ${msg}</p>
  `;
  document.getElementById("varInUseModal").classList.add("is-active");
}

function removeUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();
  if (!name) return;

  let usedInOtherUserVars = false;
  let usedAsLHS = false;
  let usedAsRHS = false;

  // 🔍 1. Check if variable is used in other user-defined variables
  for (let v of userDefinedVariables) {
    if (v.name !== name) {
      const exprString = JSON.stringify(v.expression);
      if (exprString.includes(`"${name}"`)) {
        usedInOtherUserVars = true;
        break;
      }
    }
  }

  // 🔍 2. Check if variable is used in LHS of condition rows
  const lhsSelects = document.querySelectorAll(".condition-variable");
  usedAsLHS = Array.from(lhsSelects).some(select => select.value === name);

  // 🔍 3. Check if variable is used in RHS of condition rows
  const rhsSelects = document.querySelectorAll(".rhs-variable-dropdown");
  usedAsRHS = Array.from(rhsSelects).some(select => select.value === name);

  // 🚫 If used anywhere, prevent deletion
  if (usedInOtherUserVars || usedAsLHS || usedAsRHS) {
    let msg = `⚠️ Cannot delete "${name}" because it is used `;
    if (usedInOtherUserVars) msg += `in another user-defined variable.`;
    else if (usedAsLHS) msg += `as a variable in a condition row (LHS).`;
    else if (usedAsRHS) msg += `as a variable in a condition row (RHS).`;
    alert(msg);
    return;
  }

  // ✅ 1. Remove from DOM
  box?.remove();

  // ✅ 2. Remove from global registry
  userDefinedVariables = userDefinedVariables.filter(v => v.name !== name);

  // ✅ 3. Remove from all condition dropdowns
  const dropdowns = document.querySelectorAll(".condition-variable, .rhs-variable-dropdown");
  dropdowns.forEach(dd => {
    const options = dd.querySelectorAll("option");
    options.forEach(opt => {
      if (opt.value === name) opt.remove();
    });
  });

  // ✅ 4. Remove from sessionStorage
  const saved = sessionStorage.getItem("userDefinedVariables");
  if (saved) {
    try {
      const parsed = JSON.parse(saved).filter(v => v.name !== name);
      sessionStorage.setItem("userDefinedVariables", JSON.stringify(parsed));
    } catch (err) {
      console.warn("⚠️ Session storage cleanup failed:", err);
    }
  }

  // ✅ 5. Inform backend (optional)
  fetch('/api/user_variable/delete/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body: JSON.stringify({ name })
  }).then(res => {
    if (!res.ok) {
      console.error(`❌ Failed to delete ${name} from DB`);
    }
  }).catch(err => {
    console.error('❌ AJAX Delete Error:', err);
  });
}
function formatExpressionText(expression) {
  return expression.map(item => {
    if (item.type === "variable") {
      const paramStr = (item.parameters || []).map(p => `${p.key}=${p.value}`).join(', ');
      return `${item.name}(${paramStr})`;
    } else if (item.type === "operator") {
      return ` ${item.value} `;
    } else if (item.type === "value") {
      return item.value;
    } else {
      return '';
    }
  }).join('');
}

function formatExpressionPreview(expression) {
  if (!Array.isArray(expression)) return "";
  return expression.map(part => {
    if (part.type === "value") return part.value;
    if (part.type === "variable") return part.name || part.value;
    if (part.type === "operator") return part.value;
    return "";
  }).join(" ");
}

function addExpressionVariable(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  // Group and sort indicators by category
  const grouped = {};
  indicators.forEach(v => {
    const cat = v.category || "uncategorized";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(v);
  });

  const categoryNames = Object.keys(grouped).sort(); // sort category list alphabetically

  let dropdownHtml =  buildVariableDropdown();  

  categoryNames.forEach(cat => {
    const sortedVars = grouped[cat].sort((a, b) => a.display_name.localeCompare(b.display_name));
    dropdownHtml += `<optgroup label="${cat.charAt(0).toUpperCase() + cat.slice(1)}">`;
    sortedVars.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.display_name}</option>`;
    });
    dropdownHtml += `</optgroup>`;
  });

  // ✅ Include all previously saved user-defined variables
  if (userDefinedVariables.length > 0) {
    const sortedUserVars = [...userDefinedVariables].sort((a, b) => a.name.localeCompare(b.name));
    dropdownHtml += `<optgroup label="User Defined">`;
    sortedUserVars.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.name}</option>`;
    });
    dropdownHtml += `</optgroup>`;
  }

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right"
        onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})">
      </button>
      <select class="inline-variable-dropdown"
        onchange="renderInlineVariableParams(this, ${index}); validateExpressionBuilder(${index})"
        style="width: 200px;">
        ${dropdownHtml}
      </select>
      <div class="parameters mt-1"></div>
    </div>`;

  target.appendChild(wrapper);
  validateExpressionBuilder(index);

  // ✅ Initialize Select2 with category formatting
  setTimeout(() => {
    const $dropdown = $(wrapper).find('.inline-variable-dropdown');
    $dropdown.select2({
      width: '200px',
      placeholder: "Search variable",
      allowClear: true,
      templateResult: formatDropdownItem
    });
  }, 0);
}

function addExpressionOperator(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right" onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
      <div class="select">
        <select onchange="validateExpressionBuilder(${index})">
          <option value="+">+</option>
          <option value="-">-</option>
          <option value="*">*</option>
          <option value="/">/</option>
          <option value="%">%</option>
        </select>
      </div>
    </div>`;
  target.appendChild(wrapper);
  validateExpressionBuilder(index);
}

function addExpressionValue(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right" onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
      <input type="number" step="any" placeholder="e.g. 1.5" class="input is-small" oninput="validateExpressionBuilder(${index})">
    </div>`;
  target.appendChild(wrapper);
  validateExpressionBuilder(index);
}

function updateUserVariableHiddenJSON(index) {
  const container = document.getElementById(`expression_builder_${index}`);
  const hiddenInput = document.getElementById(`user_constant_input_${index}`);

  if (!container || !hiddenInput) {
    console.warn(`🚨 Could not find container or hidden input for variable ${index}`);
    return;
  }

  const items = container.querySelectorAll('.expression-item');
  const expression = [];

  items.forEach(item => {
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    if (isVariable) {
      const varName = isVariable.value;
      const params = [];
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) params.push({ key, value: p.value });
      });
      expression.push({ type: 'variable', name: varName, parameters: params });
    } else if (isOperator) {
      const value = item.querySelector('select').value;
      expression.push({ type: 'operator', value });
    } else if (isValue) {
      const value = item.querySelector('input').value;
      expression.push({ type: 'value', value });
    }
  });

  hiddenInput.value = JSON.stringify({ name: document.querySelector(`input[name='user_constant_name_${index}']`).value.trim(), expression });
}


function preloadUserDefinedVariables() {
  const container = document.getElementById("userConstantsContainer");
  container.innerHTML = "";

  if (!Array.isArray(userDefinedVariables)) return;

  userDefinedVariables.forEach((variable, index) => {
    const section = document.createElement("div");
    section.className = "box";
    section.id = `user_var_box_${index}`;

    // Build HTML for full expression UI
    section.innerHTML = `
      <div class="is-flex is-justify-content-space-between is-align-items-center mb-2">
        <input class="input is-small" name="user_constant_name_${index}" value="${variable.name}" placeholder="Enter variable name" />
        <div>
          <button type="button" class="button is-small is-warning mr-1" onclick="editUserConstant(${index})">✏️ Edit</button>
          <button type="button" class="button is-small is-danger" onclick="removeUserConstant(${index})">❌ Delete</button>
        </div>
      </div>

      <div id="expression_builder_${index}" class="expression-builder mb-2"></div>
      <div id="expr_error_box_${index}" class="notification is-danger is-light" style="display: none;"></div>

      <div class="is-flex is-justify-content-space-between">
   <span id="const_preview_${index}" class="has-text-info">${formatExpressionText(variable.expression)}</span>
      </div>

      </div>

         <input type="hidden" id="user_constant_input_${index}" name="user_variable_json_${index}" />
 
    `;

    container.appendChild(section);

    // Restore the expression into builder
    loadExpressionUIFromJSON(`expression_builder_${index}`, variable.expression);

    // Save hidden input for form submission
    updateUserVariableHiddenJSON(index);

    // Inject into dropdowns
    const dropdowns = document.querySelectorAll('.condition-variable, .inline-variable-dropdown');
    dropdowns.forEach(dd => {
      if (![...dd.options].some(o => o.value === variable.name)) {
        const opt = document.createElement("option");
        opt.value = variable.name;
        opt.textContent = variable.name;
        dd.appendChild(opt);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", preloadUserDefinedVariables);


function addLeg() {
  const container = document.getElementById("legsContainer");
  const legIndex = document.querySelectorAll(".leg-block").length;
  const instrumentSelectId = `instrument_select_${legIndex}_${Date.now()}`;
  const legDiv = document.createElement("div");
  legDiv.classList.add("box", "leg-block", "mt-5");

  legDiv.innerHTML = `
    <h2 class="subtitle">Leg ${legIndex + 1}</h2>
    <div class="field">
      <label class="label">Instrument</label>
      <div class="select is-fullwidth">
        <select id="${instrumentSelectId}" class="instrument-dropdown" name="instrument_name[]" onchange="populateExpiryAndStrike(this, ${legIndex})" required style="width: 100%;">
          <option value="">--Select--</option>
          ${instruments.map(i => `<option value="${i.name}">${i.name}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Expiry</label>
      <div class="select">
        <select name="expiry_date[]" id="expiry_${legIndex}" required></select>
      </div>
    </div>
    <div class="field">
      <label class="label">Strike</label>
      <div class="select">
        <select name="strike_price[]" id="strike_${legIndex}" required></select>
      </div>
    </div>
    <div class="field">
      <label class="label">Option Type</label>
      <div class="select">
        <select name="option_type[]" required>
          <option value="CE">Call (CE)</option>
          <option value="PE">Put (PE)</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Order Direction</label>
      <div class="select">
        <select name="order_direction[]" required>
          <option value="BUY">Buy</option>
          <option value="SELL">Sell</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Order Type</label>
      <div class="select">
        <select name="order_type[]" required>
          <option value="MARKET">Market</option>
          <option value="LIMIT">Limit</option>
          <option value="LIMITTHENMARKET">LimitThenMarket</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Entry Conditions</label>
      <div id="entry_conditions_${legIndex}" class="condition-group"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addRootCondition('entry_conditions_${legIndex}', this)">➕ Condition</button>
    </div>

    <div class="field">
      <label class="label">Exit Conditions</label>
      <div id="exit_conditions_${legIndex}" class="condition-group"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addRootCondition('exit_conditions_${legIndex}', this)">➕ Condition</button>
    </div>
  `;

  container.appendChild(legDiv);

  // Activate Select2 on instrument dropdown
  setTimeout(() => {
    $(`#${instrumentSelectId}`).select2({
      width: '100%',
      placeholder: "Search symbol",
      allowClear: true
    });
  }, 0);
}


function populateExpiryAndStrike(selectEl, legIndex) {
  const selected = selectEl.value;
  const expirySelect = document.getElementById(`expiry_${legIndex}`);
  const strikeSelect = document.getElementById(`strike_${legIndex}`);
  const matches = instruments.filter(i => i.name === selected);

  let expiries = new Set();
  let strikes = new Set();

  matches.forEach(i => {
    (i.expiries || []).forEach(e => expiries.add(e));
    (i.strikes || []).forEach(s => strikes.add(s));
  });

  expirySelect.innerHTML = [...expiries].sort().map(e => `<option value="${e}">${e}</option>`).join('');
  strikeSelect.innerHTML = [...strikes].sort((a, b) => a - b).map(s => `<option value="${s}">${s}</option>`).join('');
}

function addConditionGroup(containerId) {
  const container = document.getElementById(containerId);
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;
  const div = document.createElement("div");
  div.classList.add("box", "nested-condition", "mt-3");

  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition Group</strong>
      <button type="button" class="delete" onclick="this.closest('.nested-condition').remove()"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow(this)">➕ Add Condition</button>
  `;

  container.appendChild(div);
}

function addConditionRow(target) {
  let container;
  if (typeof target === 'string') {
    container = document.getElementById(target);
  } else {
    container = target.closest('.nested-condition')?.querySelector('.conditions');
  }
  if (!container) return;

  const isWrapped = container.closest('.nested-condition');
  if (!isWrapped) {
    const wrapper = document.createElement('div');
    wrapper.classList.add("box", "nested-condition", "mt-3");
    const groupId = `group_${Math.random().toString(36).substring(2, 8)}`;
    wrapper.innerHTML = `
      <div class="is-flex is-justify-content-space-between mb-2">
        <strong>Condition Group</strong>
        <button type="button" class="delete" onclick="this.closest('.nested-condition').remove()"></button>
      </div>
      <div class="field">
        <label class="label">Connector</label>
        <div class="select">
          <select class="group-connector">
            <option value="AND">AND</option>
            <option value="OR">OR</option>
          </select>
        </div>
      </div>
      <div class="conditions" id="${groupId}"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${groupId}')">➕ Add Condition</button>
    `;
    container.appendChild(wrapper);
    return;
  }

  const row = document.createElement("div");
  row.classList.add("is-flex", "is-align-items-center", "mb-2", "condition-row");

  // Variable Dropdown (LHS)
  const lhsSelectWrapper = document.createElement("div");
  lhsSelectWrapper.className = "select mr-2";
  const lhsSelect = document.createElement("select");
  lhsSelect.className = "condition-variable inline-variable-dropdown";
  lhsSelect.innerHTML = getAllVariableOptionsHTML();
  lhsSelect.onchange = function () {
    renderConditionVariableParams(this);
  };
  lhsSelectWrapper.appendChild(lhsSelect);

  // Parameters (LHS)
  const paramWrapper = document.createElement("div");
  paramWrapper.className = "condition-parameters mr-2";

  // Operator Dropdown
  const operatorSelectWrapper = document.createElement("div");
  operatorSelectWrapper.className = "select mr-2";
  const operatorSelect = document.createElement("select");
  operatorSelect.className = "condition-operator";
  operatorSelect.innerHTML = `
    <option value=">">&gt;</option>
    <option value="<">&lt;</option>
    <option value=">=">&gt;=</option>
    <option value="<=">&lt;=</option>
    <option value="==">==</option>
    <option value="!=">!=</option>
  `;
  operatorSelectWrapper.appendChild(operatorSelect);

  // RHS Mode Toggle
  const rhsModeWrapper = document.createElement("div");
  rhsModeWrapper.className = "select mr-2";
  const rhsModeSelect = document.createElement("select");
  rhsModeSelect.className = "rhs-mode";
  rhsModeSelect.innerHTML = `
    <option value="value">Value</option>
    <option value="variable">Variable</option>
  `;
  rhsModeWrapper.appendChild(rhsModeSelect);

  // RHS Input (Value)
  const rhsValueInput = document.createElement("input");
  rhsValueInput.type = "text";
  rhsValueInput.placeholder = "Value";
  rhsValueInput.className = "input mr-2 rhs-input condition-value";
  rhsValueInput.style.width = "150px";

  // RHS Input (Variable dropdown)
  const rhsVarSelectWrapper = document.createElement("div");
  rhsVarSelectWrapper.className = "select mr-2 rhs-input";
  rhsVarSelectWrapper.style.display = "none";
  const rhsVarSelect = document.createElement("select");
  rhsVarSelect.className = "rhs-variable-dropdown";
  rhsVarSelect.innerHTML = getAllVariableOptionsHTML();
  rhsVarSelectWrapper.appendChild(rhsVarSelect);

  rhsModeSelect.onchange = function () {
    if (rhsModeSelect.value === "value") {
      rhsValueInput.style.display = "inline-block";
      rhsVarSelectWrapper.style.display = "none";
    } else {
      rhsValueInput.style.display = "none";
      rhsVarSelectWrapper.style.display = "inline-block";
    }
  };

  // Delete Condition Button
  const deleteBtn = document.createElement("button");
  deleteBtn.className = "delete";
  deleteBtn.type = "button";
  deleteBtn.onclick = function () {
    row.remove();
  };

  // Subgroup Button
  const subgroupBtn = document.createElement("button");
  subgroupBtn.className = "button is-small is-warning ml-2";
  subgroupBtn.type = "button";
  subgroupBtn.textContent = "➕ Subgroup";
  subgroupBtn.onclick = function () {
    addSubGroupToCondition(this);
  };

  // Assemble condition row
  row.appendChild(lhsSelectWrapper);
  row.appendChild(paramWrapper);
  row.appendChild(operatorSelectWrapper);
  row.appendChild(rhsModeWrapper);
  row.appendChild(rhsValueInput);
  row.appendChild(rhsVarSelectWrapper);
  row.appendChild(deleteBtn);
  row.appendChild(subgroupBtn);

  container.appendChild(row);

  // Initialize Select2
  $(lhsSelect).select2({ width: 'auto', placeholder: 'Select Variable' });
  $(rhsVarSelect).select2({ width: 'auto', placeholder: 'Select Variable' });
}

function addSubGroupToCondition(button) {
  const parentRow = button.parentElement;
  if (parentRow.querySelector('.nested-condition')) return;

  const container = document.createElement('div');
  container.classList.add("nested-condition", "ml-4", "mt-2");
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;

  container.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Nested Subgroup</strong>
      <button type="button" class="delete" onclick="removeSubGroup(this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;

  parentRow.appendChild(container);
  button.style.display = 'none';
  button.setAttribute('data-original-display', 'true');
}

function restoreAddSubGroupButton(deleteBtn) {
  const parent = deleteBtn.closest('.condition-row');
  const existingButton = parent.querySelector('button[data-original-text]');
  if (!existingButton) {
    const btn = document.createElement('button');
    btn.className = "button is-small is-warning ml-2";
    btn.textContent = "➕ Subgroup";
    btn.type = "button";
    btn.onclick = function() { addSubGroupToCondition(this); };
    parent.appendChild(btn);
  }
}

function removeSubGroup(deleteBtn) {
  const subgroupDiv = deleteBtn.closest('.nested-condition');
  const parentRow = subgroupDiv.parentElement;
  subgroupDiv.remove();

  const addBtn = parentRow.querySelector('button[data-original-display]');
  if (addBtn) {
    addBtn.style.display = 'inline-block';
    addBtn.removeAttribute('data-original-display');
  } else {
    const newBtn = document.createElement('button');
    newBtn.className = "button is-small is-warning ml-2";
    newBtn.textContent = "➕ Subgroup";
    newBtn.type = "button";
    newBtn.onclick = function () { addSubGroupToCondition(this); };
    parentRow.appendChild(newBtn);
  }
}
function extractConditions(container) {
  const conditions = [];
  const rows = container.querySelectorAll('.condition-row');
  rows.forEach(row => {
    const variable = row.querySelector('.condition-variable')?.value;
    const operator = row.querySelector('.condition-operator')?.value;
    const connector = row.querySelector('.group-connector')?.value || 'AND';

    // LHS Parameters
    const paramDiv = row.querySelector('.condition-parameters');
    const paramInputs = paramDiv ? paramDiv.querySelectorAll('input, select') : [];
    const lhsParams = {};
    paramInputs.forEach(p => {
      const key = p.name.split('_').pop();
      lhsParams[key] = p.value;
    });

    // RHS: either value or variable
    const rhsType = row.querySelector('.rhs-mode')?.value || 'value';
    let rhs = { type: rhsType };
    if (rhsType === 'value') {
      rhs.value = row.querySelector('.condition-value')?.value || '';
    } else {
      const rhsVar = row.querySelector('.rhs-variable-dropdown')?.value;
      const rhsParamDiv = row.querySelector('.rhs-variable-dropdown')?.closest('.rhs-input')?.querySelectorAll('input, select');
      const rhsParams = {};
      rhsParamDiv?.forEach(p => {
        const key = p.name?.split('_')?.pop();
        rhsParams[key] = p.value;
      });
      rhs.name = rhsVar;
      rhs.parameters = rhsParams;
    }

    const cond = {
      lhs: {
        name: variable,
        parameters: lhsParams
      },
      operator,
      rhs,
      connector,
      children: []
    };

    const subgroup = row.querySelector('.nested-condition');
    if (subgroup) {
      cond.children = extractConditions(subgroup);
    }

    conditions.push(cond);
  });

  return conditions;
}


function addRootCondition(containerId, button) {
  const container = document.getElementById(containerId);
  if (container.querySelector('.nested-condition')) return;

  const div = document.createElement('div');
  div.classList.add("nested-condition", "mt-2");
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;

  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition</strong>
      <button type="button" class="delete" onclick="removeRootCondition('${containerId}', this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;
  container.appendChild(div);
  button.style.display = 'none';
  button.setAttribute('data-root-btn', 'true');
}

function removeRootCondition(containerId, deleteBtn) {
  const block = deleteBtn.closest('.nested-condition');
  const parent = document.getElementById(containerId);
  block.remove();

  const existing = parent.parentElement.querySelector('button[data-root-btn]');
  if (existing) {
    existing.style.display = 'inline-block';
    existing.removeAttribute('data-root-btn');
  } else {
    const newBtn = document.createElement('button');
    newBtn.className = "button is-small is-link mt-2";
    newBtn.textContent = "➕ Condition";
    newBtn.type = "button";
    newBtn.onclick = function () { addRootCondition(containerId, this); };
    parent.appendChild(newBtn);
  }
}


function renderPython(conditions, indent = 1) {
  const pad = '  '.repeat(indent);
  let code = '';

  conditions.forEach(cond => {
    // Format LHS
    const lhsParams = Object.entries(cond.lhs.parameters || {})
      .map(([k, v]) => `${k}='${v}'`).join(', ');
    const lhsStr = `${cond.lhs.name}(${lhsParams})`;

    // Format RHS
    let rhsStr = '';
    if (cond.rhs.type === 'value') {
      rhsStr = cond.rhs.value;
    } else if (cond.rhs.type === 'variable') {
      const rhsParams = Object.entries(cond.rhs.parameters || {})
        .map(([k, v]) => `${k}='${v}'`).join(', ');
      rhsStr = `${cond.rhs.name}(${rhsParams})`;
    }

    code += `${pad}if (${lhsStr} ${cond.operator} ${rhsStr}) {\n`;

    if (cond.children && cond.children.length > 0) {
      code += renderPython(cond.children, indent + 1);
    } else {
      code += `${'  '.repeat(indent + 1)}// action\n`;
    }

    code += `${pad}}\n`;
  });

  return code;
}


function showPreview() {
  const legs = document.querySelectorAll('.leg-block');
  const jsonPreview = document.getElementById('jsonPreview');
  const pythonPreview = document.getElementById('pythonPreview');
  const previewBox = document.getElementById('jsonPreviewBox');
  const results = [];
  let python = '';

legs.forEach((leg, idx) => {
    const entry = extractConditions(document.getElementById(`entry_conditions_${idx}`));
    const exit = extractConditions(document.getElementById(`exit_conditions_${idx}`));
    results.push({ leg: idx + 1, entry_conditions: entry, exit_conditions: exit });
    python += `// Leg ${idx + 1} Entry\n`;
    python += renderPython(entry, 1);
    python += `\n// Leg ${idx + 1} Exit\n`;
    python += renderPython(exit, 1);
    python += '\n';
  });

  jsonPreview.textContent = JSON.stringify(results, null, 2);
  pythonPreview.textContent = python;
  previewBox.style.display = 'block';
}
const form = document.getElementById("algoForm");
form.addEventListener("submit", function(e) {
  //const legs = document.querySelectorAll('.leg-block');
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

    {% if not editing %}
    // AJAX check only for "Add" mode
    fetch(`/check_algo_name/?name=${encodeURIComponent(name)}`)
      .then(res => res.json())
      .then(data => {
        if (data.valid) {
          feedback.textContent = "";
          feedback.style.display = "none";
          algoNameInput.classList.remove("is-danger");
          defineBtn.disabled = !fund;
        } else {
          feedback.textContent = data.message;
          feedback.style.display = "block";
          algoNameInput.classList.add("is-danger");
          defineBtn.disabled = true;
        }
      })
      .catch(() => {
        feedback.textContent = "Error checking algorithm name.";
        feedback.style.display = "block";
        defineBtn.disabled = true;
        algoNameInput.classList.add("is-danger");
      });
    {% endif %}
  }

  // Attach validation listeners
  algoNameInput.addEventListener("input", validateFields);
  fundInput.addEventListener("input", validateFields);

  {% if is_edit_mode %}
  // 1. Show strategy section immediately
  document.getElementById("strategySection").style.display = "block";
  document.getElementById("defineStrategyBtn").style.display = "none";

  // 2. Pre-fill top fields
  algoNameInput.value = "{{ algo.algo_name|escapejs }}";
  fundInput.value = "{{ algo.minimum_fund_reqd|default:'' }}";
  document.querySelector("textarea[name='Algo_description']").value = `{{ algo.algo_description|escapejs }}`;
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

  {% endif %}
});

function restoreConditionTree(containerId, conditions) {
  const container = document.getElementById(containerId);
  const rootBtn = container.querySelector('button[data-root-btn]');
  if (rootBtn) rootBtn.click();

  const target = container.querySelector('.conditions');
  if (!target) return;

  conditions.forEach(cond => {
    const row = document.createElement("div");
    row.className = "condition-row is-flex is-align-items-center mb-2";

    const varDropdown = document.createElement("select");
    varDropdown.className = "condition-variable inline-variable-dropdown";
    varDropdown.innerHTML = getAllVariableOptionsHTML();
    varDropdown.value = cond.lhs.name;
    varDropdown.onchange = () => renderConditionVariableParams(varDropdown);

    const paramWrapper = document.createElement("div");
    paramWrapper.className = "condition-parameters mr-2";

    row.appendChild(wrapElement(varDropdown));
    row.appendChild(paramWrapper);

    renderConditionVariableParams(varDropdown);
    for (const [key, val] of Object.entries(cond.lhs.parameters || {})) {
      const input = paramWrapper.querySelector(`[name$="${key}"]`);
      if (input) input.value = val;
    }

    // Operator
    const opSelect = document.createElement("select");
    opSelect.className = "condition-operator";
    opSelect.innerHTML = `<option value=">">&gt;</option>
      <option value="<">&lt;</option>
      <option value=">=">&gt;=</option>
      <option value="<=">&lt;=</option>
      <option value="==">==</option>
      <option value="!=">!=</option>`;
    opSelect.value = cond.operator;
    row.appendChild(wrapElement(opSelect));

    // RHS Type switch
    const rhsModeSelect = document.createElement("select");
    rhsModeSelect.className = "rhs-mode";
    rhsModeSelect.innerHTML = `<option value="value">Value</option><option value="variable">Variable</option>`;
    rhsModeSelect.value = cond.rhs.type;

    row.appendChild(wrapElement(rhsModeSelect));

    // RHS: either value or variable
    const rhsValueInput = document.createElement("input");
    rhsValueInput.className = "condition-value input";
    rhsValueInput.style.width = "100px";
    rhsValueInput.value = cond.rhs.value || "";
    row.appendChild(rhsValueInput);

    const rhsVarSelect = document.createElement("select");
    rhsVarSelect.className = "rhs-variable-dropdown";
    rhsVarSelect.innerHTML = getAllVariableOptionsHTML();
    rhsVarSelect.value = cond.rhs.name || "";
    rhsVarSelect.style.display = "none";
    row.appendChild(rhsVarSelect);

    if (cond.rhs.type === "variable") {
      rhsValueInput.style.display = "none";
      rhsVarSelect.style.display = "inline-block";
    }

    rhsModeSelect.onchange = () => {
      if (rhsModeSelect.value === "value") {
        rhsValueInput.style.display = "inline-block";
        rhsVarSelect.style.display = "none";
      } else {
        rhsValueInput.style.display = "none";
        rhsVarSelect.style.display = "inline-block";
      }
    };

    row.appendChild(rhsVarSelect);

    target.appendChild(row);

    // Recursively add children
    if (cond.children?.length) {
      const subgroupBtn = document.createElement("button");
      subgroupBtn.className = "button is-small is-warning ml-2";
      subgroupBtn.textContent = "➕ Subgroup";
      subgroupBtn.onclick = () => addSubGroupToCondition(subgroupBtn);
      row.appendChild(subgroupBtn);

      addSubGroupToCondition(subgroupBtn);
      const subContainer = row.querySelector('.nested-condition .conditions');
      restoreConditionTree(subContainer.id, cond.children);
    }
  });
}

function wrapElement(el) {
  const div = document.createElement("div");
  div.className = "select mr-2";
  div.appendChild(el);
  return div;
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


</script>
{% endblock %}
