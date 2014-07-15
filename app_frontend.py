""" Starts the frontend """

import web

import frontend.pages
import frontend.session


urls = (
    '/', 'frontend.pages.index.IndexPage',
    '/index', 'frontend.pages.index.IndexPage',
    '/course/([^/]+)', 'frontend.pages.course.CoursePage',
    '/course/([^/]+)/([^/]+)', 'frontend.pages.tasks.TaskPage',
    '/admin/([^/]+)', 'frontend.pages.admin_course.AdminCourseStudentListPage',
    '/admin/([^/]+)/student/([^/]+)', 'frontend.pages.admin_course.AdminCourseStudentInfoPage',
    '/admin/([^/]+)/student/([^/]+)/([^/]+)', 'frontend.pages.admin_course.AdminCourseStudentTaskPage',
    '/admin/([^/]+)/tasks', 'frontend.pages.admin_course.AdminCourseTaskListPage',
    '/admin/([^/]+)/task/([^/]+)', 'frontend.pages.admin_course.AdminCourseTaskInfoPage',
)

app = web.application(urls, globals())

if __name__ == "__main__":
    frontend.session.init(app)

    #Must be done after frontend.session.init(app)
    import frontend.base
    def notfound():
        return web.notfound(frontend.base.renderer.notfound())
    app.notfound = notfound
    #Idem
    import frontend.submission_manager
    frontend.submission_manager.initBackendInterface()

    app.run()