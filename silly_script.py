import streamlit as st
import datetime
import calendar
import os
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AMOUNT = float(os.getenv('AMOUNT', 600))
SECRET_CODE = os.getenv('SECRET_CODE', 'default_code')

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

st.title("Mystery Budget")

# Authentication
if not st.session_state.authenticated:
    entered_code = st.text_input("Enter Secret Code:", type="password")
    if st.button("Login"):
        if entered_code == SECRET_CODE:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid secret code")

# Show the rest of the app only if authenticated
if st.session_state.authenticated:
    # Add month selector
    today = datetime.date.today()
    first_possible_date = today.replace(year=today.year-1, month=1, day=1)
    selected_month = st.date_input(
        "Select Month:",
        value=today,
        min_value=first_possible_date,
        max_value=today
    )
    selected_month = selected_month.replace(day=1)

    # Calculate daily rate for the selected month
    days_in_month = calendar.monthrange(selected_month.year, selected_month.month)[1]
    daily_rate = AMOUNT / days_in_month

    # Initialize session state for spent money from file
    if 'spent_money' not in st.session_state or 'current_month' not in st.session_state or st.session_state.current_month != selected_month:
        df = load_spent_money(selected_month)
        st.session_state.spent_money = df['amount'].sum()
        st.session_state.current_month = selected_month

    # Display current budget status
    st.header("Budget Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Money Spent",
            value=f"${st.session_state.spent_money:.2f}"
        )
    with col2:
        remainder = AMOUNT - st.session_state.spent_money
        st.metric(
            label="Remaining Budget",
            value=f"${remainder:.2f}",
            delta=f"${remainder:.2f}",
            delta_color="inverse"
        )

    # Calculate first and last day of selected month
    first_day = selected_month.replace(day=1)
    last_day = selected_month.replace(day=calendar.monthrange(selected_month.year, selected_month.month)[1])

    # Input for spending money
    spent = st.number_input("Enter amount spent:", min_value=0.0, value=0.0, step=0.1)

    # Date input
    expense_date = st.date_input(
        "Date:",
        value=today,
        min_value=first_day,
        max_value=last_day
    )

    if st.button("Record Expense"):
        st.session_state.spent_money += spent
        save_expense(spent, expense_date)
        st.rerun()

    # Add spending visualization
    st.header("Spending Visualization")
    df = load_spent_money(selected_month)
    if not df.empty:
        # Sort by date and calculate cumulative sum
        df = df.sort_values('date')
        df['cumulative_spent'] = df['amount'].cumsum()
        
        # Create a date range for the ideal spending line
        date_range = pd.date_range(start=df['date'].min(), end=selected_month.replace(day=calendar.monthrange(selected_month.year, selected_month.month)[1]))
        
        # Create ideal spending DataFrame
        ideal_df = pd.DataFrame({
            'date': date_range,
            'ideal_spending': [daily_rate * (i + 1) for i in range(len(date_range))]
        })
        
        # Merge actual and ideal spending
        plot_df = pd.merge(
            ideal_df, 
            df.groupby('date')['cumulative_spent'].last().reset_index(), 
            on='date', 
            how='left'
        )
        plot_df = plot_df.fillna(method='ffill')
        
        # Create the line chart
        fig = px.line(plot_df, x='date', 
                      y=['ideal_spending', 'cumulative_spent'],
                      line_shape='linear')
        
        fig.update_traces(line=dict(width=4))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No spending data available yet.")

def load_spent_money(selected_month):
    # Example implementation: Load data from a CSV file
    file_name = f"{selected_month.strftime('%B').lower()}_{selected_month.year}.csv"
    if os.path.exists(file_name):
        return pd.read_csv(file_name)
    else:
        return pd.DataFrame(columns=['date', 'amount'])

def save_expense(amount, date):
    # Example implementation: Save data to a CSV file
    file_name = f"{date.strftime('%B').lower()}_{date.year}.csv"
    if os.path.exists(file_name):
        df = pd.read_csv(file_name)
    else:
        df = pd.DataFrame(columns=['date', 'amount'])
    
    new_entry = pd.DataFrame({'date': [date], 'amount': [amount]})
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(file_name, index=False)


