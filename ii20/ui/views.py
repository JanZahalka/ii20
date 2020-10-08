from django.shortcuts import render


# Create your views here.
def tetris(request):
    return render(request, 'ui/tetris.html')
