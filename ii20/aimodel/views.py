from django.contrib.auth import authenticate, login, logout
from django.template import loader
from django.http import (HttpResponse, JsonResponse,
                         HttpResponseForbidden, HttpResponseBadRequest)
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import json

from aimodel.AnalyticSession import AnalyticSession
from data.DatasetConfigManager import DatasetConfigManager


def index(request, err_msg=None):
    """
    Renders the index page.
    """
    template = loader.get_template("aimodel/index.html")
    context = {}

    context["err_msg"] = err_msg

    return HttpResponse(template.render(context, request))


@require_POST
def log_in(request):
    """
    Handles login.
    """

    # Get the username and password
    username = request.POST.get("username")
    password = request.POST.get("password")

    if not username or not password:
        return index(request, "Invalid credentials!")

    # Authenticate and log in
    user = authenticate(username=username, password=password)

    if user:
        login(request, user)
        return redirect("/main")
    else:
        return index(request, "Invalid credentials!")


def main(request):
    """
    Renders the main page behind login.
    """

    if not request.user.is_authenticated:
        return redirect("/")

    template = loader.get_template("aimodel/main.html")
    context = dict()
    context["datasets"] = DatasetConfigManager.loaded_datasets_list()

    return HttpResponse(template.render(context, request))


@require_POST
def analytics_session(request):
    """
    Starts a new analytic session.
    """

    if not request.user.is_authenticated:
        return redirect("/")

    try:
        dataset = request.POST["dataset"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    if "analytics" in request.session:
        del request.session["analytics"]

    request.session["analytics"] = AnalyticSession(dataset)

    bucket_info = request.session["analytics"].bucket_info()

    template = loader.get_template("ui/analytics.html")

    context = dict()
    context["init_buckets"] = json.dumps(bucket_info["buckets"])
    context["init_bucket_ordering"] =\
        json.dumps(bucket_info["bucket_ordering"])

    return HttpResponse(template.render(context, request))


def log_out(request):
    """
    Logs the user out.
    """

    if request.user.is_authenticated:
        logout(request)

    return redirect("/")


def _check_session_valid(request):
    """
    A helper function checking whether the user is logged in and the session
    data is present.
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden(reason="Access denied!")

    if "analytics" not in request.session:
        err = "Could not fetch analytic session data."
        return HttpResponseBadRequest(reason=err)

    return None


def bucket_info(request):
    """
    Fetches information about current buckets.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    return JsonResponse(request.session["analytics"].bucket_info())


def create_bucket(request):
    """
    Creates a bucket.
    """
    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    try:
        request.session["analytics"].create_bucket()
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def delete_bucket(request):
    """
    Deletes a bucket.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket_id = request_data["bucket_id"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].delete_bucket(bucket_id)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def rename_bucket(request):
    """
    Renames a bucket.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket_id = request_data["bucket_id"]
        new_bucket_name = request_data["new_bucket_name"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].rename_bucket(bucket_id, new_bucket_name)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def swap_buckets(request):
    """
    Swaps the position of two buckets.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket1_id = request_data["bucket1_id"]
        bucket2_id = request_data["bucket2_id"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].swap_buckets(bucket1_id, bucket2_id)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def toggle_bucket(request):
    """
    Toggles (activates/deactivates) a bucket.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket_id = request_data["bucket_id"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].toggle_bucket(bucket_id)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def interaction_round(request):
    """
    Performs an interaction round, providing new image suggestions.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    user_feedback = json.loads(request.body)

    try:
        suggs = request.session["analytics"].interaction_round(user_feedback)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse(suggs, safe=False)


@require_POST
def bucket_view_data(request):
    """
    Obtains bucket view data, i.e., the images in the bucket with bucket
    confidences.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket_id = request_data["bucket_id"]
        sort_by = request_data["sort_by"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        bucket_view_data =\
            request.session["analytics"].bucket_view_data(bucket_id, sort_by)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse(bucket_view_data, safe=False)


def toggle_mode(request):
    """
    Toggles between Tetris/grid.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request.session["analytics"].toggle_mode()

    return JsonResponse({})


@require_POST
def grid_set_size(request):
    """
    Resizes the grid.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        dim = request_data["dim"]
        new_size = request_data["new_size"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        new_grid_data = request.session["analytics"].grid_set_size(dim,
                                                                   new_size)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse(new_grid_data, safe=False)


@require_POST
def transfer_images(request):
    """
    Transfers (moves/copies) images between buckets.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        images = request_data["images"]
        bucket_src = request_data["bucket_src"]
        bucket_dst = request_data["bucket_dst"]
        mode = request_data["mode"]
        sort_by = request_data["sort_by"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].transfer_images(images,
                                                     bucket_src, bucket_dst,
                                                     mode)
        bucket_view_data =\
            request.session["analytics"].bucket_view_data(bucket_src, sort_by)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse(bucket_view_data, safe=False)


@require_POST
def fast_forward(request):
    """
    Fast-forwards a bucket.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    try:
        bucket = request_data["bucket"]
        n_ff = request_data["n_ff"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].fast_forward(bucket, n_ff)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


@require_POST
def ff_commit(request):
    """
    Commits a fast-forward.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    request_data = json.loads(request.body)

    print(request_data)

    try:
        bucket = request_data["bucket"]
    except KeyError:
        err = "Invalid request params!"
        return HttpResponseBadRequest(reason=err)

    try:
        request.session["analytics"].ff_commit(bucket)
    except ValueError as e:
        return HttpResponseBadRequest(reason=str(e))

    return JsonResponse({})


def end_session(request):
    """
    Ends an analytic session.
    """

    session_check = _check_session_valid(request)

    if session_check:
        return session_check

    del request.session["analytics"]

    response = {
        "redirect_url": "/main"
    }

    return JsonResponse(response)
