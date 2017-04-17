# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Andrey Antukh <niwi@niwi.nz>
# Copyright (C) 2014-2016 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014-2016 David Barragán <bameda@dbarragan.com>
# Copyright (C) 2014-2016 Alejandro Alonso <alejandro.alonso@kaleidos.net>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from taiga.base.api import throttling


class AnonRateThrottle(throttling.AnonRateThrottle):
    scope = "anon"
    throttled_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

    def allow_request(self, request, view):
        if request.method not in self.throttled_methods:
            return True
        return super().allow_request(request, view)


class UserRateThrottle(throttling.UserRateThrottle):
    scope = "user"
    throttled_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

    def allow_request(self, request, view):
        if request.method not in self.throttled_methods:
            return True
        return super().allow_request(request, view)
