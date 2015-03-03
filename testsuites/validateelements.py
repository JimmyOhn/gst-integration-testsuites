

# -*- Mode: Python -*- vi:si:et:sw=4:sts=4:ts=4:syntax=python
#
# Copyright (c) 2015,Thibault Saunier <thibault.saunier@collabora.com>
#               2015,Vineeth T M <vineeth.tm@samsung.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
The GstValidate default testsuite
"""

from gi.repository import Gst
from gi.repository import GObject

TEST_MANAGER = "validate"


def pspec_is_numeric(prop):
    return prop.value_type in [GObject.TYPE_INT, GObject.TYPE_INT64,
                               GObject.TYPE_UINT, GObject.TYPE_UINT64,
                               GObject.TYPE_LONG, GObject.TYPE_ULONG,
                               GObject.TYPE_DOUBLE]


def get_pipe_and_populate(test_manager, klass, fname, prop, loop):
    prop_value = Gst.ElementFactory.make(fname, None).get_property(prop.name)

    if prop.value_type == GObject.TYPE_BOOLEAN:
        if loop is 1:
            bool_value = False
        else:
            bool_value = True
        cname = fname + " %s=%s" % (prop.name, bool_value)
        tname = fname + "%s=%s" % (prop.name, bool_value)
    elif pspec_is_numeric(prop):
        if loop is 2:
            int_value = prop.default_value
        elif loop is 1:
            int_value = prop.minimum
        else:
            int_value = prop.maximum
        cname = fname + " %s=%s" % (prop.name, int_value)
        tname = fname + "%s=%s" % (prop.name, int_value)
    else:
        cname = fname + " %s=%s" % (prop.name, prop_value)
        tname = fname + "%s=%s" % (prop.name, prop_value)

    if "Audio" in klass:
        cpipe = "audiotestsrc num-buffers=20 ! %s " % (cname)
        sink = "! audioconvert ! %(audiosink)s"
    elif "Video" in klass:
        cpipe = "videotestsrc num-buffers=20 ! %s " % (cname)
        sink = "! videoconvert ! %(videosink)s"
    else:
        return None

    if test_manager.options.mute:
        cpipe += "! fakesink"
    else:
        cpipe += "%s" % (sink)

    return (tname, cpipe)


def setup_tests(test_manager, options):
    print("Setting up tests to validate all elements")
    pipelines_descriptions = []
    test_manager.set_default_blacklist([
        ("validate.launch_pipeline.videocrop*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=743910"),
        ("validate.launch_pipeline.videobox*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=743909"),
        ("validate.launch_pipeline.simplevideomark*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=743908"),
        ("validate.launch_pipeline.exclusion*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=743907"),
        ("validate.launch_pipeline.quarktv*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=743906"),
        ("validate.launch_pipeline.frei0r*",
         "video filter plugins"),
        ("validate.launch_pipeline.fieldanalysis*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=744188"),
        ("validate.launch_pipeline.interleave*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=744211"),
        ("validate.launch_pipeline.spectrum*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=744213"),
        ("validate.launch_pipeline.level*",
         "https://bugzilla.gnome.org/show_bug.cgi?id=745515"),
        ("validate.launch_pipeline.smpte*",
         "smpte cannot be tested with simple pipeline. Hence excluding"),
    ])
    valid_scenarios = ["play_15s"]
    Gst.init(None)
    factories = Gst.Registry.get().get_feature_list(Gst.ElementFactory)
    for element_factory in factories:
        audiosrc = False
        audiosink = False
        videosrc = False
        videosink = False
        klass = element_factory.get_metadata("klass")
        fname = element_factory.get_name()
        props = Gst.ElementFactory.make(fname, None).list_properties()
        padstemplates = element_factory.get_static_pad_templates()

        if "" in klass:
            if "Audio" not in klass and "Video" not in klass:
                continue
            for padtemplate in padstemplates:
                if padtemplate.static_caps.string:
                    caps = padtemplate.get_caps()
                    for i in xrange(caps.get_size()):
                        structure = caps.get_structure(i)
                        if "audio/x-raw" in structure.get_name():
                            if padtemplate.direction == Gst.PadDirection.SRC:
                                audiosrc = True
                            elif padtemplate.direction == Gst.PadDirection.SINK:
                                audiosink = True
                        elif "video/x-raw" in structure.get_name():
                            if padtemplate.direction == Gst.PadDirection.SRC:
                                videosrc = True
                            elif padtemplate.direction == Gst.PadDirection.SINK:
                                videosink = True
            if (audiosink is False and videosink is False) or (audiosrc is False and videosrc is False):
                continue
            for prop in props:
                if "name" in prop.name or "parent" in prop.name or "qos" in prop.name or \
                   "latency" in prop.name or "message-forward" in prop.name:
                    continue
                if (prop.flags & GObject.ParamFlags.WRITABLE) and \
                   (prop.flags & GObject.ParamFlags.READABLE):
                    if prop.value_type == GObject.TYPE_BOOLEAN:
                        loop = 2
                    elif pspec_is_numeric(prop):
                        loop = 3
                    else:
                        loop = 0

                    while loop:
                        loop -= 1
                        description = get_pipe_and_populate(test_manager, klass,
                                                            fname, prop, loop)
                        if None is not description:
                            pipelines_descriptions.append(description)

    # No restriction about scenarios that are potentially used
    test_manager.add_scenarios([scenario.name for scenario in
                               test_manager.scenarios_manager.get_scenario(None)])
    test_manager.add_generators(test_manager.GstValidatePipelineTestsGenerator
                                ("validate_elements", test_manager,
                                    pipelines_descriptions=pipelines_descriptions,
                                    valid_scenarios=valid_scenarios))

    return True
