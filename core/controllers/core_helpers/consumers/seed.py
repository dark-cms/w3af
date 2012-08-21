'''
seed.py

Copyright 2012 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import traceback

from multiprocessing.dummy import Queue, Process

import core.controllers.outputManager as om

from core.controllers.w3afException import (w3afMustStopException, 
                                            w3afMustStopOnUrlError)
from core.controllers.core_helpers.update_urls_in_kb import update_kb
from core.controllers.core_helpers.consumers.constants import POISON_PILL
from core.controllers.w3afException import w3afException
from core.data.request.frFactory import create_fuzzable_requests


class seed(Process):
    '''
    Consumer thread that takes fuzzable requests from a Queue that's populated
    by the crawl plugins and identified vulnerabilities by performing various
    requests.
    '''
    
    def __init__(self, w3af_core):
        '''
        @param w3af_core: The w3af core that we'll use for status reporting
        '''
        super(seed, self).__init__()
        
        self._w3af_core = w3af_core
        
        # See documentation in the property below
        self._out_queue = Queue()
    
    def get_result(self, timeout=0.5):
        return self._out_queue.get_nowait() 
    
    def has_pending_work(self):
        return self._out_queue.qsize() != 0
    
    def join(self):
        return

    def terminate(self):
        return
    
    def seed_output_queue(self, target_urls):
        '''
        Create the first fuzzable request objects based on the targets and put
        them in the output Queue.
        
        This will start the whole discovery process, since plugins are going
        to consume from that Queue and then put their results in it again in 
        order to continue discovering.
        '''
        # We only want to scan pages that are in current scope
        in_scope = lambda fr: fr.getURL().getDomain() == url.getDomain()

        for url in target_urls:
            try:
                #
                #    GET the initial target URLs in order to save them
                #    in a list and use them as our bootstrap URLs
                #
                response = self._w3af_core.uri_opener.GET(url, cache=True)
            except (w3afMustStopOnUrlError, w3afException, w3afMustStopException), w3:
                om.out.error('The target URL: %s is unreachable.' % url)
                om.out.error('Error description: %s' % w3)
            except Exception, e:
                om.out.error('The target URL: %s is unreachable '
                             'because of an unhandled exception.' % url)
                om.out.error('Error description: "%s". See debug '
                             'output for more information.' % e)
                om.out.error('Traceback for this error: %s' % 
                             traceback.format_exc())
            else:
                all_fuzzable_requests = create_fuzzable_requests(response)
                filtered_seeds = filter(in_scope, all_fuzzable_requests )
                
                for seed in filtered_seeds:
                    self._out_queue.put( (None, None, seed) )
                    
                    # Update the list / set that lives in the KB
                    update_kb(seed)
                
        self._out_queue.put( POISON_PILL )