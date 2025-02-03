import re

from django.db import models

RE_DEFERRED = re.compile("_Deferred_.*")


class ShowFieldBase:
    """base class for the ShowField... model mixins, does the work"""

    # cause nicer multiline PolymorphicQuery output
    polymorphic_query_multiline_output = True

    polymorphic_showfield_type = False
    polymorphic_showfield_content = False
    polymorphic_showfield_deferred = False

    # these may be overridden by the user
    polymorphic_showfield_max_line_width = None
    polymorphic_showfield_max_field_width = 20
    polymorphic_showfield_old_format = False

    def __repr__(self):
        return self.__str__()

    def _showfields_get_content(self, field_name, field_type=type(None)):
        "helper for __unicode__"
        content = getattr(self, field_name)
        if self.polymorphic_showfield_old_format:
            out = ": "
        else:
            out = " "
        if issubclass(field_type, models.ForeignKey):
            if content is None:
                out += "None"
            else:
                out += content.__class__.__name__
        elif issubclass(field_type, models.ManyToManyField):
            out += f"{content.count()}"
        elif isinstance(content, int):
            out += str(content)
        elif content is None:
            out += "None"
        else:
            txt = str(content)
            max_len = self.polymorphic_showfield_max_field_width
            if len(txt) > max_len:
                txt = f"{txt[: max_len - 2]}.."
            out += f'"{txt}"'
        return out

    def _showfields_add_regular_fields(self, parts):
        "helper for __unicode__"
        done_fields = set()
        for field in self._meta.fields + self._meta.many_to_many:
            if field.name in self.polymorphic_internal_model_fields or "_ptr" in field.name:
                continue
            if field.name in done_fields:
                continue  # work around django diamond inheritance problem
            done_fields.add(field.name)

            out = field.name

            # if this is the standard primary key named "id", print it as we did with older versions of django_polymorphic
            if field.primary_key and field.name == "id" and type(field) == models.AutoField:
                out += f" {getattr(self, field.name)}"

            # otherwise, display it just like all other fields (with correct type, shortened content etc.)
            else:
                if self.polymorphic_showfield_type:
                    out += f" ({type(field).__name__}"
                    if field.primary_key:
                        out += "/pk"
                    out += ")"

                if self.polymorphic_showfield_content:
                    out += self._showfields_get_content(field.name, type(field))

            parts.append((False, out, ","))

    def _showfields_add_dynamic_fields(self, field_list, title, parts):
        "helper for __unicode__"
        parts.append((True, f"- {title}", ":"))
        for field_name in field_list:
            out = field_name
            content = getattr(self, field_name)
            if self.polymorphic_showfield_type:
                out += f" ({type(content).__name__})"
            if self.polymorphic_showfield_content:
                out += self._showfields_get_content(field_name)

            parts.append((False, out, ","))

    def __str__(self):
        # create list ("parts") containing one tuple for each title/field:
        # ( bool: new section , item-text , separator to use after item )

        # start with model name
        parts = [(True, RE_DEFERRED.sub("", self.__class__.__name__), ":")]

        # add all regular fields
        self._showfields_add_regular_fields(parts)

        # add annotate fields
        if hasattr(self, "polymorphic_annotate_names"):
            self._showfields_add_dynamic_fields(self.polymorphic_annotate_names, "Ann", parts)

        # add extra() select fields
        if hasattr(self, "polymorphic_extra_select_names"):
            self._showfields_add_dynamic_fields(
                self.polymorphic_extra_select_names, "Extra", parts
            )

        if self.polymorphic_showfield_deferred:
            fields = self.get_deferred_fields()
            if fields:
                fields_str = ",".join(sorted(fields))
                parts.append((False, f"deferred[{fields_str}]", ""))

        # format result

        indent = len(self.__class__.__name__) + 5
        indentstr = "".rjust(indent)
        out = ""
        xpos = 0
        possible_line_break_pos = None

        for i in range(len(parts)):
            new_section, p, separator = parts[i]
            final = i == len(parts) - 1
            if not final:
                next_new_section, _, _ = parts[i + 1]

            if (
                self.polymorphic_showfield_max_line_width
                and xpos + len(p) > self.polymorphic_showfield_max_line_width
                and possible_line_break_pos is not None
            ):
                rest = out[possible_line_break_pos:]
                out = out[:possible_line_break_pos]
                out += f"\n{indentstr}{rest}"
                xpos = indent + len(rest)

            out += p
            xpos += len(p)

            if not final:
                if not next_new_section:
                    out += separator
                    xpos += len(separator)
                out += " "
                xpos += 1

            if not new_section:
                possible_line_break_pos = len(out)

        return f"<{out}>"


class ShowFieldType(ShowFieldBase):
    """model mixin that shows the object's class and it's field types"""

    polymorphic_showfield_type = True


class ShowFieldContent(ShowFieldBase):
    """model mixin that shows the object's class, it's fields and field contents"""

    polymorphic_showfield_content = True


class ShowFieldTypeAndContent(ShowFieldBase):
    """model mixin, like ShowFieldContent, but also show field types"""

    polymorphic_showfield_type = True
    polymorphic_showfield_content = True
