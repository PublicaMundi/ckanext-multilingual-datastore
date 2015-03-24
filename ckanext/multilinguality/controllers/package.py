from ckan.lib.base import (
    c, request, response, render, abort, redirect, BaseController)

class UserController(BaseController):

    def resource_translate(self):
        #user_dict = self._check_access()
        #self._setup_template_variables(user_dict)
        print 'EEEEEEE'
        return render('package/resource_translate.html')

