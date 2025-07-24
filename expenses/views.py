#from django.shortcuts import render

# Create your views here.
# expenses/views.py
from django.shortcuts import render, redirect
from .forms import ExpenseForm
from .models import Expense, PocketMoney
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db import models
from collections import defaultdict
from datetime import date, timedelta
import json
import csv
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from io import TextIOWrapper
import re
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/add_expense.html', {'form': form})

def expense_list(request):
    # expenses = Expense.objects.all().order_by('-date')
    # total = sum(exp.amount for exp in expenses)
    # return render(request, 'expenses/expense_list.html', {'expenses': expenses, 'total': total})
    today = now().date()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    start_of_month = today.replace(day=1)

    # Filter expenses for the current user
    monthly_expenses = Expense.objects.filter(user=request.user, date__gte=start_of_month)
    weekly_expenses = Expense.objects.filter(user=request.user, date__gte=start_of_week)
    monthly_total = monthly_expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    weekly_total = weekly_expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    today_total = Expense.objects.filter(user=request.user, date=today).aggregate(total=models.Sum('amount'))['total'] or 0
    yesterday_total = Expense.objects.filter(user=request.user, date=yesterday).aggregate(total=models.Sum('amount'))['total'] or 0
    # Pocket Money this month
    monthly_income = PocketMoney.objects.filter(user=request.user, date_received__gte=start_of_month).aggregate(total=models.Sum('amount'))['total'] or 0
    # Calculate remaining money
    money_left = monthly_income - monthly_total
    if money_left < 0:
        money_left = 0

    # # Category totals
    # category_summary = Expense.objects.values('category').annotate(total=Sum('amount'))
    # labels = [item['category'] for item in category_summary]
    # data = [float(item['total']) for item in category_summary]  # ✅ ensure it's float

    # from django.db.models import Sum

    # monthly_total = Expense.objects.filter(...).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'monthly_expenses': monthly_expenses,
        'weekly_expenses': weekly_expenses,
        'monthly_total': monthly_total,
        'weekly_total': weekly_total,
        'today_total': today_total,
        'yesterday_total': yesterday_total,
        'monthly_income': monthly_income,
        'money_left': money_left,
        # 'category_labels': json.dumps(labels),
        # 'category_data': json.dumps(data),
    }
    import calendar
    from django.db.models.functions import ExtractWeekDay, ExtractMonth, ExtractYear
    # Weekly trend for dashboard
    week_expenses = (
        Expense.objects.filter(user=request.user, date__gte=start_of_week, date__lte=today)
        .annotate(weekday=ExtractWeekDay('date'))
        .values('weekday')
        .annotate(total=models.Sum('amount'))
        .order_by('weekday')
    )
    week_labels = [calendar.day_abbr[(i-2)%7] for i in range(2,9)]  # Use short names
    week_totals_map = {e['weekday']: float(e['total']) for e in week_expenses}
    week_totals = [week_totals_map.get(i, 0) for i in range(2,9)]
    # Monthly trend for dashboard (current year)
    current_year = today.year
    monthly_data = (
        Expense.objects.filter(user=request.user, date__year=current_year)
        .annotate(month=ExtractMonth('date'))
        .values('month')
        .annotate(total=models.Sum('amount'))
        .order_by('month')
    )
    month_labels = [calendar.month_abbr[m['month']] for m in monthly_data]
    month_totals = [float(m['total']) for m in monthly_data]
    # Previous month total
    if start_of_month.month == 1:
        prev_month = 12
        prev_year = start_of_month.year - 1
    else:
        prev_month = start_of_month.month - 1
        prev_year = start_of_month.year
    prev_month_expenses = Expense.objects.filter(
        user=request.user,
        date__year=prev_year,
        date__month=prev_month
    )
    prev_month_total = prev_month_expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    # Pocket money percentage left
    pocket_money_percent_left = 0
    if monthly_income:
        pocket_money_percent_left = (money_left / monthly_income) * 100
        if pocket_money_percent_left < 0:
            pocket_money_percent_left = 0
    context.update({
        'week_labels_json': json.dumps(week_labels),
        'week_totals_json': json.dumps(week_totals),
        'month_labels_json': json.dumps(month_labels),
        'month_totals_json': json.dumps(month_totals),
        'prev_month_total': prev_month_total,
        'pocket_money_percent_left': pocket_money_percent_left,
    })
    return render(request, 'expenses/expense_list.html', context)

def edit_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/edit_expense.html', {'form': form})


def delete_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list')
    return render(request, 'expenses/delete_expense.html', {'expense': expense})


from .models import PocketMoney
from .forms import PocketMoneyForm

def add_pocket_money(request):
    if request.method == 'POST':
        form = PocketMoneyForm(request.POST)
        if form.is_valid():
            pocket_money = form.save(commit=False)
            pocket_money.user = request.user
            pocket_money.save()
            return redirect('view_pocket_money')
    else:
        form = PocketMoneyForm()
    return render(request, 'expenses/add_pocket_money.html', {'form': form})


def view_pocket_money(request):
    pocket_money = PocketMoney.objects.filter(user=request.user).order_by('-date_received')

    today = now().date()
    start_of_month = today.replace(day=1)
    monthly_income = pocket_money.filter(date_received__gte=start_of_month).aggregate(total=models.Sum('amount'))['total'] or 0

    return render(request, 'expenses/view_pocket_money.html', {
        'pocket_money': pocket_money,
        'monthly_income': monthly_income
    })

def edit_pocket_money(request, id):
    pocket_money = get_object_or_404(PocketMoney, id=id, user=request.user)
    if request.method == 'POST':
        form = PocketMoneyForm(request.POST, instance=pocket_money)
        if form.is_valid():
            form.save()
            return redirect('view_pocket_money')
    else:
        form = PocketMoneyForm(instance=pocket_money)
    return render(request, 'expenses/edit_pocket_money.html', {'form': form})



def weekly_expenses(request):
    from django.db.models import Q, Avg, Max, Min, Sum
    from django.db.models.functions import ExtractYear, ExtractWeek
    from datetime import date
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    # Get filter params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_week = request.GET.get('week')

    # Set default to current year/week if not provided
    if not selected_year:
        selected_year = str(today.year)
    if not selected_week:
        selected_week = str(today.isocalendar()[1])

    # Get all available years and weeks from expenses
    all_years = Expense.objects.filter(user=request.user).annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    all_weeks = Expense.objects.filter(user=request.user).annotate(week=ExtractWeek('date')).values_list('week', flat=True).distinct().order_by('week')

    # Start with all expenses for the user
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year:
        expenses = expenses.filter(date__year=selected_year)
    if selected_week:
        expenses = expenses.filter(date__week=selected_week)

    # Group by day name
    weekly_grouped = defaultdict(list)
    for expense in expenses.order_by('date'):
        day = expense.date.strftime('%A')
        weekly_grouped[day].append(expense)

    # Get all unique categories for the filter dropdown
    categories = Expense.objects.filter(user=request.user).values_list('category', flat=True).distinct()

    # Calculate total for the filtered week
    week_total = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Calculate summary info
    expense_count = expenses.count()
    average_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    max_amount_val = expenses.aggregate(max=Max('amount'))['max'] or 0
    min_amount_val = expenses.aggregate(min=Min('amount'))['min'] or 0
    # Find the category with the highest total spending
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    if category_totals:
        top_category = category_totals[0]['category']
        top_category_amount = category_totals[0]['total']
    else:
        top_category = None
        top_category_amount = 0

    return render(request, 'expenses/weekly_expenses.html', {
        'weekly_grouped': dict(weekly_grouped),
        'categories': categories,
        'week_total': week_total,
        'expense_count': expense_count,
        'average_amount': average_amount,
        'max_amount': max_amount_val,
        'min_amount': min_amount_val,
        'top_category': top_category,
        'top_category_amount': top_category_amount,
        'all_years': all_years,
        'all_weeks': all_weeks,
        'selected_year': selected_year,
        'selected_week': selected_week,
    })


def monthly_expenses(request):
    from django.db.models import Avg, Max, Min
    from django.db.models.functions import ExtractYear, ExtractMonth
    from datetime import datetime
    monthly_grouped = defaultdict(list)
    # Get filter params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    # Set default to current year/month if not provided
    today = datetime.today()
    if not selected_year:
        selected_year = str(today.year)
    if not selected_month:
        selected_month = str(today.month)

    # Get all available years and months from expenses
    all_years = Expense.objects.filter(user=request.user).annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    all_months = [
        (i, datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)
    ]

    # Start with all expenses for the user
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year:
        expenses = expenses.filter(date__year=selected_year)
    if selected_month:
        expenses = expenses.filter(date__month=selected_month)

    for exp in expenses:
        month = exp.date.strftime('%B %Y')
        monthly_grouped[month].append(exp)

    # Calculate summary info
    month_total = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    expense_count = expenses.count()
    average_amount = expenses.aggregate(avg=Avg('amount'))['avg'] or 0
    max_amount_val = expenses.aggregate(max=Max('amount'))['max'] or 0
    min_amount_val = expenses.aggregate(min=Min('amount'))['min'] or 0
    categories = Expense.objects.filter(user=request.user).values_list('category', flat=True).distinct()

    # Find the category with the highest total spending
    from django.db.models import Sum
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    if category_totals:
        top_category = category_totals[0]['category']
        top_category_amount = category_totals[0]['total']
    else:
        top_category = None
        top_category_amount = 0

    return render(request, 'expenses/monthly_expenses.html', {
        'monthly_grouped': dict(monthly_grouped),
        'month_total': month_total,
        'expense_count': expense_count,
        'average_amount': average_amount,
        'max_amount': max_amount_val,
        'min_amount': min_amount_val,
        'categories': categories,
        'top_category': top_category,
        'top_category_amount': top_category_amount,
        'all_years': all_years,
        'all_months': all_months,
        'selected_year': selected_year,
        'selected_month': selected_month,
    })

from django.shortcuts import render
from .models import Expense
from django.db.models import Sum
from collections import defaultdict

def monthly_overview(request):
    # Aggregate total expenses by month and year
    monthly_summary = (
        Expense.objects
        .values('month', 'year')
        .annotate(total=Sum('amount'))
        .order_by('-year', '-month')
    )

    return render(request, 'expenses/monthly_overview.html', {
        'monthly_summary': monthly_summary
    })


def monthly_detail(request, year, month):
    expenses = Expense.objects.filter(month=month, year=year).order_by('-date')

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'expenses/monthly_detail.html', {
        'expenses': expenses,
        'month': month,
        'year': year,
        'total': total
    })


def download_monthly_expenses(request):
    # Use the same filtering logic as before
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')

    # Only include expenses for the current user
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    if start_date:
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__lte=end_date)
    if category:
        expenses = expenses.filter(category=category)
    if min_amount:
        expenses = expenses.filter(amount__gte=min_amount)
    if max_amount:
        expenses = expenses.filter(amount__lte=max_amount)
    if selected_year and selected_year != "None":
        expenses = expenses.filter(date__year=selected_year)
    if selected_month and selected_month != "None":
        expenses = expenses.filter(date__month=selected_month)

    # Calculate totals by category
    from django.db.models import Sum
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    overall_total = sum(cat['total'] for cat in category_totals)

    # Determine month and year label for the report
    import calendar
    if selected_month and selected_month != "None":
        try:
            month_label = calendar.month_name[int(selected_month)]
        except Exception:
            month_label = str(selected_month)
    else:
        month_label = None
    if selected_year and selected_year != "None":
        year_label = str(selected_year)
    else:
        year_label = None
    if month_label and year_label:
        period_label = f"{month_label} {year_label}"
    elif month_label:
        period_label = month_label
    elif year_label:
        period_label = year_label
    else:
        period_label = ""

    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="monthly_expenses.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Monthly Expenses Report")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 70, f"Period: {period_label}")

    # Show overall total at the top
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 100, f"Total Amount: Rs. {overall_total:.2f}")

    # Table headers for category summary
    p.setFont("Helvetica-Bold", 12)
    y = height - 140
    p.drawString(50, y, "Category")
    p.drawString(250, y, "Total Amount")

    # Table rows for each category
    p.setFont("Helvetica", 11)
    y -= 20
    for cat in category_totals:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, "Category")
            p.drawString(250, y, "Total Amount")
            p.setFont("Helvetica", 11)
            y -= 20
        p.drawString(50, y, cat['category'])
        p.drawString(250, y, f"Rs. {cat['total']:.2f}")
        y -= 18

    p.showPage()
    p.save()
    return response


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('expense_list')  # This will redirect to /expenses/
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'expenses/login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                user = User.objects.create_user(username=username, password=password1)
                login(request, user)
                return redirect('expense_list')
            except IntegrityError:
                messages.error(request, 'Username already exists.')
    return render(request, 'expenses/signup.html')


def logout_view(request):
    logout(request)
    return redirect('welcome')


def analysis(request):
    from django.db.models.functions import ExtractMonth, ExtractYear, ExtractWeekDay
    from django.db.models import Sum
    from calendar import month_abbr, day_name
    import calendar
    # Monthly trend (current year)
    current_year = datetime.now().year
    monthly_data = (
        Expense.objects.filter(user=request.user, date__year=current_year)
        .annotate(month=ExtractMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    month_labels = [month_abbr[m['month']] for m in monthly_data]
    month_totals = [float(m['total']) for m in monthly_data]
    # Category breakdown (all time)
    category_data = (
        Expense.objects.filter(user=request.user)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    category_labels = [c['category'] for c in category_data]
    category_totals = [float(c['total']) for c in category_data]
    # Weekly trend (current week, Monday-Sunday)
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    week_expenses = (
        Expense.objects.filter(user=request.user, date__gte=start_of_week, date__lte=today)
        .annotate(weekday=ExtractWeekDay('date'))
        .values('weekday')
        .annotate(total=Sum('amount'))
        .order_by('weekday')
    )
    # Django's ExtractWeekDay: Sunday=1, Monday=2, ..., Saturday=7
    week_labels = [calendar.day_name[(i-2)%7] for i in range(2,9)]
    week_totals_map = {e['weekday']: float(e['total']) for e in week_expenses}
    week_totals = [week_totals_map.get(i, 0) for i in range(2,9)]
    context = {
        'month_labels_json': json.dumps(month_labels),
        'month_totals_json': json.dumps(month_totals),
        'category_labels_json': json.dumps(category_labels),
        'category_totals_json': json.dumps(category_totals),
        'week_labels_json': json.dumps(week_labels),
        'week_totals_json': json.dumps(week_totals),
    }
    return render(request, 'expenses/analysis.html', context)


def import_statement(request):
    """
    Handles uploading and parsing of UPI/Bank statement (CSV or PDF).
    GET: Show upload form.
    POST: Handle file upload, parse, and show preview for confirmation.
    """
    if request.method == 'POST' and request.POST.get('confirm_import') == '1':
        # Confirm import: get edited values from POST
        row_count = int(request.POST.get('row_count', 0))
        imported = 0
        for i in range(row_count):
            date_str = request.POST.get(f'date_{i}', '').strip()
            amount_str = request.POST.get(f'amount_{i}', '').strip()
            payee = request.POST.get(f'payee_{i}', '').strip()
            note = request.POST.get(f'note_{i}', '').strip()
            if not date_str or not amount_str:
                continue
            try:
                from datetime import datetime
                date = None
                for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%b %d, %Y %I:%M %p', '%b %d, %Y'):
                    try:
                        date = datetime.strptime(date_str, fmt).date()
                        break
                    except Exception:
                        continue
                if not date:
                    continue
                amount = float(amount_str.replace(',', ''))
                from .models import Expense
                Expense.objects.create(
                    user=request.user,
                    amount=amount,
                    category='Other',
                    date=date,
                    note=f"{payee} {note}".strip(),
                )
                imported += 1
            except Exception:
                continue
        return render(request, 'expenses/import_statement.html', {'success': f'Imported {imported} expenses.'})
    elif request.method == 'POST' and 'statement_file' in request.FILES:
        file = request.FILES['statement_file']
        file_type = request.POST.get('file_type', 'csv')
        preview_data = []
        if file_type == 'csv' and file.name.endswith('.csv'):
            try:
                csvfile = TextIOWrapper(file, encoding='utf-8')
                reader = csv.DictReader(csvfile)
                for row in reader:
                    date = row.get('Date') or row.get('date') or ''
                    amount = row.get('Amount') or row.get('amount') or ''
                    payee = row.get('Payee') or row.get('payee') or row.get('To') or ''
                    note = row.get('Note') or row.get('note') or row.get('Description') or ''
                    if date and amount:
                        preview_data.append({
                            'date': date,
                            'amount': amount,
                            'payee': payee,
                            'note': note,
                        })
            except Exception as e:
                return render(request, 'expenses/import_statement.html', {'error': f'Error parsing CSV: {e}'})
        elif file_type == 'pdf' and file.name.endswith('.pdf'):
            if not PyPDF2:
                return render(request, 'expenses/import_statement.html', {'error': 'PDF support is not installed on the server.'})
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text() + '\n'
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                i = 0
                while i < len(lines):
                    if re.match(r'^[A-Za-z]{3} \d{1,2}, \d{4}$', lines[i]):
                        date_str = lines[i]
                        time_str = ''
                        payee = ''
                        tx_type = ''
                        amount = ''
                        note = ''
                        if i+1 < len(lines) and re.match(r'^\d{2}:\d{2} [AP]M$', lines[i+1]):
                            time_str = lines[i+1]
                            i += 1
                        if i+1 < len(lines) and (lines[i+1].startswith('Paid to') or lines[i+1].startswith('Received from')):
                            payee = lines[i+1]
                            i += 1
                        j = i+1
                        while j < len(lines) and not (lines[j].startswith('DEBIT') or lines[j].startswith('CREDIT')):
                            note += lines[j] + ' '
                            j += 1
                        if j < len(lines) and lines[j].startswith('DEBIT'):
                            tx_type = 'DEBIT'
                            # Try to extract amount from the DEBIT line or the next line
                            amount_match = re.search(r'DEBIT\s*₹\s*([\d,]+)', lines[j])
                            if not amount_match and j+1 < len(lines):
                                amount_match = re.search(r'₹\s*([\d,]+)', lines[j+1])
                            if amount_match:
                                amount = amount_match.group(1).replace(',', '')
                            i = j
                            preview_data.append({
                                'date': f'{date_str} {time_str}'.strip(),
                                'amount': amount,
                                'payee': payee,
                                'note': note.strip(),
                                'type': tx_type,
                            })
                        # Ignore CREDIT transactions
                    i += 1
                if not preview_data:
                    return render(request, 'expenses/import_statement.html', {'error': 'No UPI DEBIT transactions found in PDF.'})
            except Exception as e:
                return render(request, 'expenses/import_statement.html', {'error': f'Error parsing PDF: {e}'})
        # Store preview_data in session for confirmation step
        request.session['import_preview_data'] = preview_data
        return render(request, 'expenses/import_statement.html', {'preview_data': preview_data})
    else:
        return render(request, 'expenses/import_statement.html')


def welcome(request):
    return render(request, 'expenses/welcome.html')

