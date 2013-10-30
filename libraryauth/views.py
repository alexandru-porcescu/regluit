import logging
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.views import login
from django.http import HttpResponseRedirect
from . import backends

from .models import Library
from .forms import AuthForm

logger = logging.getLogger(__name__)

def library(request, library,  
        extra_context={}, 
        template='libraryauth/library.html',
        **kwargs):
    library=get_object_or_404(Library, user__username=library)
    context={   'library':library, 
                'is_admin':  request.user.is_staff or request.user==library.user,
                'is_member': request.user.is_staff or library.has_user(request.user),
            }
    context.update(extra_context)
    return render(request, template, context)

def join_library(request, library):
    library=get_object_or_404(Library, user__username=library)
    return Authenticator(request,library).process(
            reverse('library',args=[str(library)]), 
            reverse('bad_library',args=[str(library)]), 
        )

def superlogin(request, extra_context=None, **kwargs):
    if request.method == 'POST' and request.user.is_anonymous():
        username=request.POST.get("username", "")
        try:
            user=models.User.objects.get(username=username)
            extra_context={"socials":user.profile.social_auths}
        except:
            pass
    if request.GET.has_key("add"):
        request.session["add_wishlist"]=request.GET["add"]
    return login(request, extra_context=extra_context, authentication_form=AuthForm, **kwargs)

class Authenticator:
    request=None
    library=None

    def __init__(self, request, library, *args, **kwargs):
        self.request = request
        if  isinstance(library , basestring):
            self.library = Library.objects.get(user__username=library)
        elif isinstance(library , Library):
            self.library=library
        else:
            raise Exception
        try:
            form_class = getattr(backends, self.library.backend + '_form')
            self.form = form_class(request, library, *args, **kwargs)
        except AttributeError:
            self.form = None
        
    def process(self, success_url, deny_url):
        logger.info('authenticator for %s at %s.'%(self.request.user, self.library))
        if self.library.has_user(self.request.user):
            return HttpResponseRedirect(success_url)
        backend_test= getattr(backends, self.library.backend + '_authenticate')
        if backend_test(self.request, self.library):
            if self.request.user.is_authenticated():
                self.library.add_user(self.request.user)
                return HttpResponseRedirect(success_url)
            else:
                return superlogin(self.request, extra_context={'library':self.library}, template_name='libraryauth/library_login.html')
            
        else:
            backend_authenticator= getattr(backends, self.library.backend + '_authenticator')
            return backend_authenticator().process(self, success_url, deny_url)
            
    def allowed(self):
        backend_test= getattr(backends, self.library.backend + '_authenticate')
        return  backend_test(self.request, self.library)