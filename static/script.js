document.addEventListener('DOMContentLoaded', () => {
    const transactionForm = document.getElementById('transaction-form');
    const transactionsList = document.getElementById('transactions-list');
    const totalBalanceSpan = document.getElementById('total-balance');
    const categorySummaryList = document.getElementById('category-summary-list');
    const budgetForm = document.getElementById('budget-form');
    const budgetsList = document.getElementById('budgets-list');

    // Function to fetch and display transactions
    const fetchTransactions = async () => {
        if (!transactionsList) return; // Only run if on transactions page
        try {
            const response = await fetch('/api/transactions');
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const transactions = await response.json();
            transactionsList.innerHTML = ''; // Clear existing list
            let totalBalance = 0;

            transactions.forEach(transaction => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <span>${transaction.description} (${transaction.category || 'Uncategorized'})</span>
                    <span class="amount">${transaction.amount.toFixed(2)}</span>
                `;
                transactionsList.appendChild(listItem);
                totalBalance += transaction.amount;
            });
            if (totalBalanceSpan) {
                totalBalanceSpan.textContent = totalBalance.toFixed(2);
            }
        } catch (error) {
            console.error('Error fetching transactions:', error);
        }
    };

    // Function to fetch and display category summary
    const fetchCategorySummary = async () => {
        if (!categorySummaryList) return; // Only run if on dashboard or transactions page
        try {
            const response = await fetch('/api/transactions/summary');
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const summary = await response.json();
            categorySummaryList.innerHTML = '';

            for (const category in summary) {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <span>${category || 'Uncategorized'}:</span>
                    <span class="amount">${summary[category].toFixed(2)}</span>
                `;
                categorySummaryList.appendChild(listItem);
            }
        } catch (error) {
            console.error('Error fetching category summary:', error);
        }
    };

    // Function to fetch and display budgets
    const fetchBudgets = async () => {
        if (!budgetsList) return; // Only run if on budget page
        try {
            const response = await fetch('/api/budgets');
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const budgets = await response.json();
            budgetsList.innerHTML = '';

            budgets.forEach(budget => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <span>${budget.category}:</span>
                    <span class="amount">${budget.amount.toFixed(2)}</span>
                    <button data-id="${budget.id}" class="delete-budget">Delete</button>
                `;
                budgetsList.appendChild(listItem);
            });

            // Add event listeners for delete buttons
            document.querySelectorAll('.delete-budget').forEach(button => {
                button.addEventListener('click', async (event) => {
                    const budgetId = event.target.dataset.id;
                    try {
                        const response = await fetch(`/api/budgets/${budgetId}`, {
                            method: 'DELETE',
                        });
                        if (!response.ok) {
                            if (response.status === 401) {
                                window.location.href = '/login';
                                return;
                            }
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        const result = await response.json();
                        console.log(result.message);
                        fetchBudgets(); // Refresh budgets list
                    } catch (error) {
                        console.error('Error deleting budget:', error);
                        alert(`Failed to delete budget: ${error.message}`);
                    }
                });
            });

        } catch (error) {
            console.error('Error fetching budgets:', error);
        }
    };

    // Function to add/update a budget
    if (budgetForm) { // Ensure form exists (only on budget.html)
        budgetForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const category = document.getElementById('budget-category').value;
            const amount = parseFloat(document.getElementById('budget-amount').value);

            try {
                const response = await fetch('/api/budgets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ category, amount }),
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log(result.message);
                budgetForm.reset(); // Clear form
                fetchBudgets(); // Refresh budgets list
            } catch (error) {
                console.error('Error adding/updating budget:', error);
                alert(`Failed to add/update budget: ${error.message}`);
            }
        });
    }

    // Function to add a new transaction
    if (transactionForm) { // Ensure form exists (only on transactions.html)
        transactionForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const description = document.getElementById('description').value;
            const amount = parseFloat(document.getElementById('amount').value);
            const category = document.getElementById('category').value; // Get category

            try {
                const response = await fetch('/api/transactions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ description, amount, category }),
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log(result.message);
                transactionForm.reset(); // Clear form
                fetchTransactions(); // Refresh the list
                fetchCategorySummary(); // Refresh category summary
            } catch (error) {
                console.error('Error adding transaction:', error);
                alert(`Failed to add transaction: ${error.message}`);
            }
        });
    }

    // Initial data fetch based on current page
    const path = window.location.pathname;
    if (path === '/dashboard') {
        fetchTransactions(); // For total balance on dashboard
        fetchCategorySummary();
    } else if (path === '/transactions') {
        fetchTransactions();
        fetchCategorySummary();
    } else if (path === '/budget') {
        fetchBudgets();
    }
});
