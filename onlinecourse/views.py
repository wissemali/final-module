from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Question, Choice, Submission
from .models import Course, Enrollment
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def submit(request, course_id):
    if request.method == 'POST':
        user = request.user
        course = Course.objects.get(pk=course_id)
        
        # Get the enrollment object for the user and course
        enrollment = Enrollment.objects.get(user=user, course=course)
        
        # Create a new submission object
        submission = Submission.objects.create(enrollment=enrollment)
        
        # Collect the selected choices from the form
        selected_choices = [int(key[6:]) for key in request.POST.keys() if key.startswith('choice')]
        
        # Add each selected choice to the submission object
        for choice_id in selected_choices:
            choice = Choice.objects.get(pk=choice_id)
            submission.choices.add(choice)
        
        # Redirect to show_exam_result view with the submission id
        return redirect('onlinecourse:show_exam_result', submission_id=submission.id)
    
    return render(request, 'onlinecourse/submit.html')


# <HINT> A example method to collect the selected choices from the exam form from the request object
#def extract_answers(request):
#    submitted_anwsers = []
#    for key in request.POST:
#        if key.startswith('choice'):
#            value = request.POST[key]
#            choice_id = int(value)
#            submitted_anwsers.append(choice_id)
#    return submitted_anwsers


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    
    # Get the selected choice ids from the submission record
    selected_choice_ids = submission.choices.values_list('id', flat=True)
    
    # Calculate the total score and question results
    total_score = 0
    question_results = []
    
    for question in course.question_set.all():
        selected_choices = question.choice_set.filter(id__in=selected_choice_ids)
        
        # Check if each selected choice is correct or not
        is_correct = all(choice.is_correct for choice in selected_choices)
        
        # Calculate the score for each question
        question_score = question.grade_point if is_correct else 0
        total_score += question_score
        
        # Store the question result
        question_result = {
            'question': question,
            'selected_choices': selected_choices,
            'is_correct': is_correct,
            'score': question_score
        }
        question_results.append(question_result)
    
    context = {
        'course': course,
        'submission': submission,
        'total_score': total_score,
        'question_results': question_results
    }
    
    return render(request, 'onlinecourse/show_exam_result.html', context)


